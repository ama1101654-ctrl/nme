import os
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import crud
from .database import Base, engine, get_db
from .models import AuthSession, Item, User
from .schemas import (
    AuthSessionActionResponse,
    AuthSessionCleanupResponse,
    AuthSessionResponse,
    Item,
    ItemCreate,
    LoginRequest,
    LoginResponse,
    ProductCreate,
    ProductResponse,
    RefreshTokenRequest,
    TokenRefreshResponse,
    UserCreate,
    UserResponse,
    OrderCreate,
    OrderResponse,
)
from .schemas import OrderStatusUpdate
from .schemas import MarketResponse
from .schemas import DealCreate, DealResponse, DealStatusUpdate
from .schemas import DealCompletionResponse

Base.metadata.create_all(bind=engine)


def ensure_auth_sessions_last_used_at_column():
    """Add auth_sessions.last_used_at in-place for existing SQLite DBs.

    This avoids destructive DB reset and keeps existing rows intact.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(auth_sessions)")).fetchall()
        column_names = {row[1] for row in rows}
        if 'last_used_at' not in column_names:
            conn.execute(
                text(
                    "ALTER TABLE auth_sessions "
                    "ADD COLUMN last_used_at DATETIME"
                )
            )
            conn.execute(
                text(
                    "UPDATE auth_sessions "
                    "SET last_used_at = COALESCE(created_at, expires_at, CURRENT_TIMESTAMP) "
                    "WHERE last_used_at IS NULL"
                )
            )
            conn.commit()
            return

        conn.execute(
            text(
                "UPDATE auth_sessions "
                "SET last_used_at = COALESCE(created_at, expires_at, CURRENT_TIMESTAMP) "
                "WHERE last_used_at IS NULL"
            )
        )
        conn.commit()


ensure_auth_sessions_last_used_at_column()

app = FastAPI(title="NME Backend", version="0.1.0")
bearer_scheme = HTTPBearer(auto_error=False)


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, client_key: str):
        now = monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            bucket = self._buckets.setdefault(client_key, deque())
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self.limit:
                retry_after = max(1, int(bucket[0] + self.window_seconds - now))
                raise HTTPException(
                    status_code=429,
                    detail='Too many requests',
                    headers={'Retry-After': str(retry_after)},
                )

            bucket.append(now)


def parse_csv_env(raw: str | None):
    if not raw:
        return []

    return [item.strip() for item in raw.split(',') if item.strip()]


def parse_bool_env(raw: str | None, default: bool = False):
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False

    raise RuntimeError('Boolean environment value must be true/false style text')


def load_env_value(key: str, default: str | None = None):
    value = os.getenv(key)
    if value:
        return value

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as env_file:
            for line in env_file:
                stripped = line.strip()
                if not stripped or stripped.startswith('#') or '=' not in stripped:
                    continue
                name, raw = stripped.split('=', 1)
                if name.strip() == key:
                    return raw.strip()

    return default


def get_rate_limit_window_seconds():
    raw = load_env_value('AUTH_RATE_LIMIT_WINDOW_SECONDS', '60')
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise RuntimeError('AUTH_RATE_LIMIT_WINDOW_SECONDS must be an integer') from exc

    if seconds <= 0:
        raise RuntimeError('AUTH_RATE_LIMIT_WINDOW_SECONDS must be > 0')

    return seconds


def get_auth_login_rate_limit():
    raw = load_env_value('AUTH_LOGIN_RATE_LIMIT', '10')
    try:
        limit = int(raw)
    except ValueError as exc:
        raise RuntimeError('AUTH_LOGIN_RATE_LIMIT must be an integer') from exc

    if limit <= 0:
        raise RuntimeError('AUTH_LOGIN_RATE_LIMIT must be > 0')

    return limit


def get_auth_refresh_rate_limit():
    raw = load_env_value('AUTH_REFRESH_RATE_LIMIT', '30')
    try:
        limit = int(raw)
    except ValueError as exc:
        raise RuntimeError('AUTH_REFRESH_RATE_LIMIT must be an integer') from exc

    if limit <= 0:
        raise RuntimeError('AUTH_REFRESH_RATE_LIMIT must be > 0')

    return limit


def get_client_ip(request: Request):
    direct_client_ip = request.client.host if request.client and request.client.host else 'unknown'

    if not should_trust_proxy_headers():
        return direct_client_ip

    trusted_proxy_ips = get_trusted_proxy_ips()
    if direct_client_ip not in trusted_proxy_ips:
        return direct_client_ip

    forwarded_for = request.headers.get('x-forwarded-for', '')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get('x-real-ip', '').strip()
    if real_ip:
        return real_ip

    return direct_client_ip


def get_app_env():
    value = load_env_value('APP_ENV', 'development')
    normalized = str(value).strip().lower()
    if normalized not in {'development', 'production'}:
        raise RuntimeError('APP_ENV must be development or production')
    return normalized


def is_production_env():
    return get_app_env() == 'production'


def get_dev_cors_allow_origins():
    raw = load_env_value(
        'DEV_CORS_ALLOW_ORIGINS',
        'http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:8000',
    )
    return parse_csv_env(raw)


def get_prod_cors_allow_origins():
    raw = load_env_value('PROD_CORS_ALLOW_ORIGINS', '')
    return parse_csv_env(raw)


def get_cors_allow_origins():
    if is_production_env():
        return get_prod_cors_allow_origins()

    return get_dev_cors_allow_origins()


def should_trust_proxy_headers():
    return parse_bool_env(load_env_value('TRUST_PROXY_HEADERS', 'false'), default=False)


def get_trusted_proxy_ips():
    raw = load_env_value('TRUSTED_PROXY_IPS', '')
    return set(parse_csv_env(raw))


def should_enable_csp():
    return parse_bool_env(load_env_value('SECURITY_ENABLE_CSP', 'true'), default=True)


def should_enable_hsts():
    return parse_bool_env(load_env_value('SECURITY_ENABLE_HSTS', 'true'), default=True)


def get_hsts_max_age_seconds():
    raw = load_env_value('SECURITY_HSTS_MAX_AGE_SECONDS', '31536000')
    try:
        seconds = int(raw)
    except ValueError as exc:
        raise RuntimeError('SECURITY_HSTS_MAX_AGE_SECONDS must be an integer') from exc

    if seconds <= 0:
        raise RuntimeError('SECURITY_HSTS_MAX_AGE_SECONDS must be > 0')

    return seconds


def get_production_content_security_policy():
    configured = load_env_value('PRODUCTION_CONTENT_SECURITY_POLICY')
    if configured:
        return configured

    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )


def get_jwt_secret_key():
    secret = load_env_value('JWT_SECRET_KEY')
    if not secret:
        raise RuntimeError('JWT_SECRET_KEY is required')
    return secret


def get_jwt_algorithm():
    return load_env_value('JWT_ALGORITHM', 'HS256')


def get_jwt_access_token_expire_minutes():
    raw = load_env_value('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60')
    try:
        minutes = int(raw)
    except ValueError as exc:
        raise RuntimeError('JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer') from exc

    if minutes <= 0:
        raise RuntimeError('JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be > 0')

    return minutes


def get_jwt_refresh_token_expire_days():
    raw = load_env_value('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')
    try:
        days = int(raw)
    except ValueError as exc:
        raise RuntimeError('JWT_REFRESH_TOKEN_EXPIRE_DAYS must be an integer') from exc

    if days <= 0:
        raise RuntimeError('JWT_REFRESH_TOKEN_EXPIRE_DAYS must be > 0')

    return days


def get_auth_session_cleanup_retention_days():
    raw = load_env_value('AUTH_SESSION_CLEANUP_RETENTION_DAYS', '1')
    try:
        days = int(raw)
    except ValueError as exc:
        raise RuntimeError('AUTH_SESSION_CLEANUP_RETENTION_DAYS must be an integer') from exc

    if days < 0:
        raise RuntimeError('AUTH_SESSION_CLEANUP_RETENTION_DAYS must be >= 0')

    return days


auth_login_rate_limiter = InMemoryRateLimiter(
    limit=get_auth_login_rate_limit(),
    window_seconds=get_rate_limit_window_seconds(),
)
auth_refresh_rate_limiter = InMemoryRateLimiter(
    limit=get_auth_refresh_rate_limit(),
    window_seconds=get_rate_limit_window_seconds(),
)


def enforce_login_rate_limit(request: Request):
    auth_login_rate_limiter.check(get_client_ip(request))


def enforce_refresh_rate_limit(request: Request):
    auth_refresh_rate_limiter.check(get_client_ip(request))


def create_access_token(user_id: int, session_id: int | None = None):
    expire = datetime.now(timezone.utc) + timedelta(minutes=get_jwt_access_token_expire_minutes())
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'exp': expire,
    }
    if session_id is not None:
        payload['sid'] = str(session_id)
    return jwt.encode(payload, get_jwt_secret_key(), algorithm=get_jwt_algorithm())


def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=get_jwt_refresh_token_expire_days())
    token_jti = uuid4().hex
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'jti': token_jti,
        'exp': expire,
    }
    token = jwt.encode(payload, get_jwt_secret_key(), algorithm=get_jwt_algorithm())
    return token, token_jti, expire


def decode_token(token: str, expected_type: str):
    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[get_jwt_algorithm()])
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail='Token expired') from exc
    except JWTError as exc:
        raise HTTPException(status_code=401, detail='Invalid token') from exc

    token_type = payload.get('type')
    if token_type != expected_type:
        raise HTTPException(status_code=401, detail=f'Invalid token type: expected {expected_type}')

    return payload


def get_token_user_id(payload: dict):
    subject = payload.get('sub')
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail='Invalid token subject') from exc

    if user_id <= 0:
        raise HTTPException(status_code=401, detail='Invalid token subject')

    return user_id


def validate_refresh_token_jti(payload: dict):
    token_jti = payload.get('jti')
    if not token_jti:
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    return token_jti


def get_token_session_id(payload: dict):
    session_id = payload.get('sid')
    if session_id is None:
        return None

    try:
        parsed = int(session_id)
    except (TypeError, ValueError):
        return None

    if parsed <= 0:
        return None

    return parsed


def validate_refresh_session(db: Session, refresh_jti: str):
    auth_session = crud.get_auth_session_by_refresh_jti(db=db, refresh_jti=refresh_jti)
    if auth_session is None:
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    if auth_session.revoked_at is not None:
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail='Token expired')

    return auth_session

allow_origins = get_cors_allow_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=()'

    content_type = response.headers.get('content-type', '').lower()
    if should_enable_csp() and is_production_env() and content_type.startswith('text/html'):
        response.headers['Content-Security-Policy'] = get_production_content_security_policy()

    if should_enable_hsts() and is_production_env() and request.url.scheme == 'https':
        response.headers['Strict-Transport-Security'] = f'max-age={get_hsts_max_age_seconds()}; includeSubDomains'

    return response

# Serve static frontend under /static to avoid shadowing API routes
try:
    app.mount("/static", StaticFiles(directory="static", html=True), name="frontend")
except Exception:
    pass


@app.get("/", include_in_schema=False)
def root_index():
    """Return the static index.html if present, otherwise a small JSON message."""
    try:
        return FileResponse("static/index.html")
    except Exception:
        return {"message": "NME Backend running. Visit /docs for API."}


@app.get("/health", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/items", response_model=Item, tags=["items"])
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create an item."""
    return crud.create_item(db=db, item=item)


@app.get("/items", response_model=list[Item], tags=["items"])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read items."""
    return crud.get_items(db=db, skip=skip, limit=limit)


@app.post("/products", response_model=ProductResponse, tags=["products"])
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a product listing."""
    return crud.create_product(db=db, product=product)


@app.get("/products", response_model=list[ProductResponse], tags=["products"])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read products."""
    return crud.get_products(db=db, skip=skip, limit=limit)


@app.get("/products/{product_id}", response_model=ProductResponse, tags=["products"])
def read_product(product_id: int, db: Session = Depends(get_db)):
    """Read a product by id."""
    db_product = crud.get_product(db=db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.post("/users", response_model=UserResponse, tags=["users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a user."""
    try:
        return crud.create_user(db=db, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/users", response_model=list[UserResponse], tags=["users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read users."""
    return crud.get_users(db=db, skip=skip, limit=limit)


@app.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    """Read a user by id."""
    db_user = crud.get_user(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(
    payload: LoginRequest,
    _: None = Depends(enforce_login_rate_limit),
    db: Session = Depends(get_db),
):
    """Validate existing MVP user credentials and return the authenticated user id."""
    email = payload.email.strip()
    password = payload.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    user = crud.authenticate_user(db=db, email=email, password=password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    refresh_token, refresh_jti, refresh_expires_at = create_refresh_token(user.id)
    auth_session = crud.create_auth_session(db=db, user_id=user.id, refresh_jti=refresh_jti, expires_at=refresh_expires_at)

    return {
        "access_token": create_access_token(user.id, session_id=auth_session.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "role": user.role,
    }


@app.post("/auth/refresh", response_model=TokenRefreshResponse, tags=["auth"])
def refresh_access_token(
    payload: RefreshTokenRequest,
    _: None = Depends(enforce_refresh_rate_limit),
    db: Session = Depends(get_db),
):
    """Issue a new rotated access token pair from a valid refresh token."""
    if not payload.refresh_token:
        raise HTTPException(status_code=401, detail='Refresh token is required')

    token_payload = decode_token(payload.refresh_token, expected_type='refresh')
    user_id = get_token_user_id(token_payload)
    token_jti = validate_refresh_token_jti(token_payload)
    auth_session = validate_refresh_session(db=db, refresh_jti=token_jti)
    user = crud.get_user(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')

    if auth_session.user_id != user.id:
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    crud.touch_auth_session_last_used_at(db=db, auth_session=auth_session)
    crud.revoke_auth_session(db=db, auth_session=auth_session)
    new_refresh_token, new_refresh_jti, new_refresh_expires_at = create_refresh_token(user.id)
    new_auth_session = crud.create_auth_session(
        db=db,
        user_id=user.id,
        refresh_jti=new_refresh_jti,
        expires_at=new_refresh_expires_at,
    )

    return {
        'access_token': create_access_token(user.id, session_id=new_auth_session.id),
        'refresh_token': new_refresh_token,
        'token_type': 'bearer',
    }


def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Resolve the current MVP auth user from a JWT bearer token.

    STEP 32 keeps auth deliberately simple so this dependency can later be
    replaced by JWT or another production auth mechanism.
    """
    if credentials is None or credentials.scheme.lower() != 'bearer' or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials, expected_type='access')
    user_id = get_token_user_id(payload)

    user = crud.get_user(db=db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def require_admin_user(current_user: User = Depends(get_current_auth_user)):
    """Allow access only to users with existing ADMIN role semantics."""
    if str(current_user.role or '').upper() != 'ADMIN':
        raise HTTPException(status_code=403, detail='Admin role required')
    return current_user


@app.get("/auth/me", response_model=UserResponse, tags=["auth"])
def read_auth_me(current_user: User = Depends(get_current_auth_user)):
    """Return the currently authenticated MVP user."""
    return current_user


@app.post("/auth/logout", tags=["auth"])
def logout(payload: RefreshTokenRequest, current_user: User = Depends(get_current_auth_user), db: Session = Depends(get_db)):
    """Revoke the current refresh token for the authenticated session."""
    if not payload.refresh_token:
        raise HTTPException(status_code=401, detail='Refresh token is required')

    token_payload = decode_token(payload.refresh_token, expected_type='refresh')
    token_jti = validate_refresh_token_jti(token_payload)
    user_id = get_token_user_id(token_payload)
    if user_id != current_user.id:
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    auth_session = crud.get_auth_session_by_refresh_jti(db=db, refresh_jti=token_jti)
    if auth_session is not None and auth_session.user_id == current_user.id:
        crud.revoke_auth_session(db=db, auth_session=auth_session)

    return {'status': 'logged_out'}


@app.get("/auth/sessions", response_model=list[AuthSessionResponse], tags=["auth"])
def read_auth_sessions(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: User = Depends(get_current_auth_user),
    db: Session = Depends(get_db),
):
    """Return active auth sessions for the currently authenticated user only."""
    if credentials is None or credentials.scheme.lower() != 'bearer' or not credentials.credentials:
        raise HTTPException(status_code=401, detail='Not authenticated')

    access_payload = decode_token(credentials.credentials, expected_type='access')
    current_session_id = get_token_session_id(access_payload)
    sessions = crud.get_active_auth_sessions_by_user(db=db, user_id=current_user.id)

    response = []
    for session in sessions:
        response.append(
            {
                'id': session.id,
                'created_at': session.created_at,
                'last_used_at': session.last_used_at,
                'expires_at': session.expires_at,
                'is_current': current_session_id == session.id,
            }
        )

    return response


@app.post("/auth/sessions/revoke-all", response_model=AuthSessionActionResponse, tags=["auth"])
def revoke_all_auth_sessions(current_user: User = Depends(get_current_auth_user), db: Session = Depends(get_db)):
    """Revoke all active refresh sessions for the current user."""
    crud.revoke_all_auth_sessions_for_user(db=db, user_id=current_user.id)
    return {'status': 'all_sessions_revoked'}


@app.post("/auth/sessions/{session_id}/revoke", response_model=AuthSessionActionResponse, tags=["auth"])
def revoke_auth_session(session_id: int, current_user: User = Depends(get_current_auth_user), db: Session = Depends(get_db)):
    """Revoke one session owned by the current user."""
    auth_session = crud.get_auth_session_by_id_for_user(db=db, session_id=session_id, user_id=current_user.id)
    if auth_session is None:
        raise HTTPException(status_code=404, detail='Session not found')

    if auth_session.revoked_at is not None:
        return {'status': 'already_revoked'}

    crud.revoke_auth_session(db=db, auth_session=auth_session)
    return {'status': 'revoked'}


@app.post("/auth/sessions/cleanup", response_model=AuthSessionCleanupResponse, tags=["auth"])
def cleanup_auth_sessions(
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Cleanup old expired/revoked auth sessions using retention policy."""
    retention_days = get_auth_session_cleanup_retention_days()
    deleted_count = crud.cleanup_auth_sessions(db=db, retention_days=retention_days)
    return {
        'status': 'cleaned',
        'deleted_count': deleted_count,
        'retention_days': retention_days,
    }


@app.post("/orders", response_model=OrderResponse, tags=["orders"])
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order for a product by a buyer.

    Minimal validation: ids and numeric fields must be positive.
    """
    # Basic validation
    if order.product_id <= 0 or order.buyer_id <= 0:
        raise HTTPException(status_code=400, detail="product_id and buyer_id must be > 0")
    if order.quantity <= 0 or order.price <= 0:
        raise HTTPException(status_code=400, detail="quantity and price must be > 0")

    # Ensure referenced product and user exist
    db_product = crud.get_product(db=db, product_id=order.product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db_user = crud.get_user(db=db, user_id=order.buyer_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return crud.create_order(db=db, order=order)


@app.get("/orders", response_model=list[OrderResponse], tags=["orders"])
def read_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all orders."""
    return crud.get_orders(db=db, skip=skip, limit=limit)


@app.get("/orders/{order_id}", response_model=OrderResponse, tags=["orders"])
def read_order(order_id: int, db: Session = Depends(get_db)):
    """Read a single order by id."""
    db_order = crud.get_order(db=db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@app.get("/market", response_model=list[MarketResponse], tags=["market"])
def read_market(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return current market products (those with status == 'available')."""
    products = crud.get_market_products(db=db, skip=skip, limit=limit)

    # Map Product model -> MarketResponse fields
    result = []
    for p in products:
        result.append(
            {
                "product_id": p.id,
                "metal": p.metal,
                "grade": p.grade,
                "quantity": p.quantity,
                "unit": p.unit,
                "price": p.price,
                "status": p.status,
            }
        )

    return result


@app.post("/deals", response_model=DealResponse, tags=["deals"])
def create_deal(deal: DealCreate, db: Session = Depends(get_db)):
    """Create a deal (negotiation) for a market product.

    Validations: product and buyer existence, numeric fields > 0, and product availability.
    """
    # Basic numeric validation
    if deal.product_id <= 0 or deal.buyer_id <= 0:
        raise HTTPException(status_code=400, detail="product_id and buyer_id must be > 0")
    if deal.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")
    if deal.proposed_price <= 0:
        raise HTTPException(status_code=400, detail="proposed_price must be > 0")

    # Existence checks
    db_product = crud.get_product(db=db, product_id=deal.product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db_buyer = crud.get_user(db=db, user_id=deal.buyer_id)
    if db_buyer is None:
        raise HTTPException(status_code=404, detail="Buyer not found")

    # Product must be available per Market rules
    if getattr(db_product, "status", None) != "available":
        raise HTTPException(status_code=400, detail="Product is not available")

    return crud.create_deal(db=db, deal=deal)


@app.get("/deals", response_model=list[DealResponse], tags=["deals"])
def read_deals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return all deals."""
    return crud.get_deals(db=db, skip=skip, limit=limit)


@app.get("/deals/{deal_id}", response_model=DealResponse, tags=["deals"])
def read_deal(deal_id: int, db: Session = Depends(get_db)):
    """Return a single deal by id."""
    db_deal = crud.get_deal(db=db, deal_id=deal_id)
    if db_deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return db_deal


@app.patch("/deals/{deal_id}/status", response_model=DealResponse, tags=["deals"])
def patch_deal_status(deal_id: int, status_update: DealStatusUpdate, db: Session = Depends(get_db)):
    """Update deal status following allowed transitions."""
    db_deal = crud.get_deal(db=db, deal_id=deal_id)
    if db_deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        updated = crud.update_deal_status(db=db, deal_id=deal_id, new_status=status_update.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return updated


@app.post("/deals/{deal_id}/create-order", response_model=OrderResponse, tags=["deals"])
def create_order_from_deal_endpoint(deal_id: int, db: Session = Depends(get_db)):
    """Create an Order from an AGREED Deal. Deal remains unchanged."""
    db_deal = crud.get_deal(db=db, deal_id=deal_id)
    if db_deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Use CRUD helper which encapsulates validations and duplicate prevention
    try:
        created = crud.create_order_from_deal(db=db, deal_id=deal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if created is None:
        # Shouldn't generally happen because we checked above, but keep safe
        raise HTTPException(status_code=404, detail="Deal not found")

    return created


@app.get("/deals/{deal_id}/order", response_model=OrderResponse, tags=["deals"])
def read_deal_order(deal_id: int, db: Session = Depends(get_db)):
    """Return the Order created from a Deal, if any."""
    db_deal = crud.get_deal(db=db, deal_id=deal_id)
    if db_deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    order = crud.get_order_for_deal(db=db, deal_id=deal_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found for this Deal")

    return order


@app.get("/deals/{deal_id}/completion", response_model=DealCompletionResponse, tags=["deals"])
def read_deal_completion(deal_id: int, db: Session = Depends(get_db)):
    """Return a small summary indicating whether the Deal's Order is completed."""
    db_deal = crud.get_deal(db=db, deal_id=deal_id)
    if db_deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    summary = crud.get_deal_completion(db=db, deal_id=deal_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Order not found for this Deal")

    return summary


@app.patch("/orders/{order_id}/status", response_model=OrderResponse, tags=["orders"])
def patch_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Update order status following allowed transitions."""
    # Ensure order exists
    db_order = crud.get_order(db=db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        updated = crud.update_order_status(db=db, order_id=order_id, new_status=status_update.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return updated
