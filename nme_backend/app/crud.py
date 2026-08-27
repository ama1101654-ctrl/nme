from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from sqlalchemy.orm import Session

from .models import AuthSession, Item, Product, User, Order, Deal
from .schemas import ItemCreate, ProductCreate, UserCreate, OrderCreate, DealCreate


def create_item(db: Session, item: ItemCreate) -> Item:
    """Create a new item and save it to the database."""
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_items(db: Session, skip: int = 0, limit: int = 100):
    """Return items ordered by most recent first."""
    return db.query(Item).order_by(Item.id.desc()).offset(skip).limit(limit).all()


def create_product(db: Session, product: ProductCreate) -> Product:
    """Create a new product listing and save it to the database."""
    db_product = Product(
        seller_id=product.seller_id,
        metal=product.metal,
        grade=product.grade,
        quantity=product.quantity,
        unit=product.unit,
        price=product.price,
        status=product.status,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_products(db: Session, skip: int = 0, limit: int = 100):
    """Return products ordered by most recent first."""
    return db.query(Product).order_by(Product.id.desc()).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int):
    """Return a product by id."""
    return db.query(Product).filter(Product.id == product_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user and save it to the database."""
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise ValueError("Email already registered")

    db_user = User(
        company_name=user.company_name,
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Return users ordered by most recent first."""
    return db.query(User).order_by(User.id.desc()).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    """Return a user by id."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Return a user by email."""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user using the existing MVP password field."""
    user = get_user_by_email(db=db, email=email)
    if user is None:
        return None

    if user.password != password:
        return None

    return user


def create_auth_session(db: Session, user_id: int, refresh_jti: str, expires_at: datetime) -> AuthSession:
    """Create a persisted auth session for a refresh token."""
    now_utc = datetime.now(timezone.utc)
    db_session = AuthSession(
        user_id=user_id,
        refresh_jti=refresh_jti,
        expires_at=expires_at,
        last_used_at=now_utc,
        revoked_at=None,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_auth_session_by_refresh_jti(db: Session, refresh_jti: str):
    """Return an auth session by refresh token jti."""
    return db.query(AuthSession).filter(AuthSession.refresh_jti == refresh_jti).first()


def get_auth_session_by_jti(db: Session, refresh_jti: str):
    """Backward-compatible alias for existing callers."""
    return get_auth_session_by_refresh_jti(db=db, refresh_jti=refresh_jti)


def get_active_auth_sessions_by_user(db: Session, user_id: int):
    """Return active (not revoked, not expired) auth sessions for a user."""
    now_utc = datetime.now(timezone.utc)
    return (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id)
        .filter(AuthSession.revoked_at.is_(None))
        .filter(AuthSession.expires_at > now_utc)
        .order_by(AuthSession.created_at.desc(), AuthSession.id.desc())
        .all()
    )


def get_auth_session_by_id_for_user(db: Session, session_id: int, user_id: int):
    """Return a session only when it belongs to the provided user."""
    return (
        db.query(AuthSession)
        .filter(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .first()
    )


def touch_auth_session_last_used_at(db: Session, auth_session: AuthSession):
    """Update last_used_at for a successfully used refresh session."""
    auth_session.last_used_at = datetime.now(timezone.utc)
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    return auth_session


def revoke_auth_session(db: Session, auth_session: AuthSession):
    """Mark a specific auth session revoked if needed and return it."""
    if auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.now(timezone.utc)
        db.add(auth_session)
        db.commit()
        db.refresh(auth_session)

    return auth_session


def revoke_all_auth_sessions_for_user(db: Session, user_id: int):
    """Revoke all active auth sessions for a user and return revoke count."""
    sessions = get_active_auth_sessions_by_user(db=db, user_id=user_id)
    if not sessions:
        return 0

    now_utc = datetime.now(timezone.utc)
    for session in sessions:
        session.revoked_at = now_utc
        db.add(session)

    db.commit()
    return len(sessions)


def revoke_auth_session_by_jti(db: Session, refresh_jti: str):
    """Mark an auth session revoked if it exists."""
    auth_session = get_auth_session_by_refresh_jti(db=db, refresh_jti=refresh_jti)
    if auth_session is None:
        return None

    return revoke_auth_session(db=db, auth_session=auth_session)


def get_expired_auth_sessions(db: Session, retention_days: int):
    """Return expired sessions older than the retention cutoff."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    return (
        db.query(AuthSession)
        .filter(AuthSession.expires_at <= cutoff)
        .order_by(AuthSession.id.asc())
        .all()
    )


def get_revoked_auth_sessions(db: Session, retention_days: int):
    """Return revoked sessions older than the retention cutoff."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    return (
        db.query(AuthSession)
        .filter(AuthSession.revoked_at.is_not(None))
        .filter(AuthSession.revoked_at <= cutoff)
        .order_by(AuthSession.id.asc())
        .all()
    )


def cleanup_auth_sessions(db: Session, retention_days: int):
    """Delete expired/revoked sessions older than the retention cutoff.

    Active sessions are never deleted because they are neither expired nor
    revoked before the cutoff.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    deleted_count = (
        db.query(AuthSession)
        .filter(
            or_(
                AuthSession.expires_at <= cutoff,
                (AuthSession.revoked_at.is_not(None) & (AuthSession.revoked_at <= cutoff)),
            )
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted_count


def create_order(db: Session, order: OrderCreate) -> Order:
    """Create a new order and save it to the database."""
    db_order = Order(
        product_id=order.product_id,
        buyer_id=order.buyer_id,
        quantity=order.quantity,
        price=order.price,
        status="PENDING",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_orders(db: Session, skip: int = 0, limit: int = 100):
    """Return orders ordered by most recent first."""
    return db.query(Order).order_by(Order.id.desc()).offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int):
    """Return an order by id."""
    return db.query(Order).filter(Order.id == order_id).first()


def update_order_status(db: Session, order_id: int, new_status: str):
    """Update the status of an order following allowed transitions.

    Returns the updated Order, or None if not found. Raises ValueError on invalid transition.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        return None

    # Define allowed transitions
    allowed = {
        "PENDING": ["ACCEPTED", "CANCELLED"],
        "ACCEPTED": ["PAID", "CANCELLED"],
        "PAID": ["SHIPPED"],
        "SHIPPED": ["COMPLETED"],
        "COMPLETED": [],
        "CANCELLED": [],
    }

    current = order.status
    # Normalize None or unexpected current status
    if current not in allowed:
        raise ValueError(f"Invalid current order status: {current}")

    if new_status == current:
        # No change; treat as successful no-op
        return order

    if new_status not in allowed[current]:
        raise ValueError(f"Invalid order status transition: {current} -> {new_status}")

    # Apply change
    order.status = new_status
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_market_products(db: Session, skip: int = 0, limit: int = 100):
    """Return products that are currently available on the market.

    This function filters by the `status` field using the project's existing
    value for available products (currently "available").
    """
    return (
        db.query(Product)
        .filter(Product.status == "available")
        .order_by(Product.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_deal(db: Session, deal: DealCreate) -> Deal:
    """Create a new deal (negotiation) and save it to the database."""
    db_deal = Deal(
        product_id=deal.product_id,
        buyer_id=deal.buyer_id,
        quantity=deal.quantity,
        proposed_price=deal.proposed_price,
        status="NEGOTIATING",
    )
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


def get_deals(db: Session, skip: int = 0, limit: int = 100):
    """Return deals ordered by most recent first."""
    return db.query(Deal).order_by(Deal.id.desc()).offset(skip).limit(limit).all()


def get_deal(db: Session, deal_id: int):
    """Return a deal by id."""
    return db.query(Deal).filter(Deal.id == deal_id).first()


def update_deal_status(db: Session, deal_id: int, new_status: str):
    """Update the status of a deal following allowed transitions.

    Returns the updated Deal, or None if not found. Raises ValueError on invalid transition.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    allowed = {
        "NEGOTIATING": ["AGREED", "REJECTED", "CANCELLED"],
        "AGREED": [],
        "REJECTED": [],
        "CANCELLED": [],
    }

    current = deal.status
    if current not in allowed:
        raise ValueError(f"Invalid current deal status: {current}")

    if new_status == current:
        return deal

    if new_status not in allowed[current]:
        raise ValueError(f"Invalid deal status transition: {current} -> {new_status}")

    deal.status = new_status
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


def create_order_from_deal(db: Session, deal_id: int):
    """Create an Order from an AGREED Deal.

    Returns the created Order, or:
      - None if deal not found
      - raises ValueError if deal not in AGREED or order already exists
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    # Deal must be AGREED
    if deal.status != "AGREED":
        raise ValueError("Deal must be AGREED to create an order")

    # Prevent duplicate: check existing order with same deal fields
    existing = (
        db.query(Order)
        .filter(
            Order.product_id == deal.product_id,
            Order.buyer_id == deal.buyer_id,
            Order.quantity == deal.quantity,
            Order.price == deal.proposed_price,
        )
        .first()
    )
    if existing:
        raise ValueError("Order already created for this Deal")

    # Create order using existing pattern
    db_order = Order(
        product_id=deal.product_id,
        buyer_id=deal.buyer_id,
        quantity=deal.quantity,
        price=deal.proposed_price,
        status="PENDING",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order_for_deal(db: Session, deal_id: int):
    """Return the Order that was created from a given Deal.

    Because Orders are not tied by foreign key to Deals in this simple schema,
    we match on the key fields used when the Order was created from the Deal.
    Returns the Order or None if not found; returns None if Deal does not exist.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    order = (
        db.query(Order)
        .filter(
            Order.product_id == deal.product_id,
            Order.buyer_id == deal.buyer_id,
            Order.quantity == deal.quantity,
            Order.price == deal.proposed_price,
        )
        .order_by(Order.id.desc())
        .first()
    )
    return order


def get_deal_completion(db: Session, deal_id: int):
    """Return a small dict describing the completion status for a Deal's Order.

    Returns None if Deal or Order not found; otherwise returns a dict with
    deal_id, order_id, status, completed (bool).
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    order = get_order_for_deal(db=db, deal_id=deal_id)
    if order is None:
        return None

    completed = (getattr(order, "status", None) == "COMPLETED")
    return {"deal_id": deal.id, "order_id": order.id, "status": order.status, "completed": completed}
