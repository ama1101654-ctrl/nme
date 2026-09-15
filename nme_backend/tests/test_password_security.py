from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, inspect, select

from app.database import SessionLocal
from app.main import get_jwt_algorithm, get_jwt_secret_key
from app.models import AuthSession, User
from app.password_security import PASSWORD_DISABLED_VALUE, migrate_legacy_passwords, verify_password


def test_new_user_password_is_hashed_before_insert():
    with SessionLocal() as db:
        user = User(
            company_name='Security Co',
            name='Secure User',
            email='secure-user@example.com',
            password='temporary-test-password',
            role='USER',
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.password == PASSWORD_DISABLED_VALUE
        assert user.password_hash != 'temporary-test-password'
        assert user.password_hash.startswith('$argon2id$')
        assert verify_password('temporary-test-password', user.password_hash) is True
        assert verify_password('wrong-password', user.password_hash) is False


def test_legacy_password_migration_is_transactional_and_preserves_identity_and_sessions(tmp_path):
    migration_engine = create_engine(f"sqlite:///{(tmp_path / 'legacy-password.db').as_posix()}")
    metadata = MetaData()
    users = Table(
        'users',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('company_name', String(150), nullable=True),
        Column('name', String(100), nullable=False),
        Column('email', String(255), nullable=False, unique=True),
        Column('password', String(255), nullable=False),
        Column('role', String(50), nullable=False),
        Column('created_at', DateTime, nullable=False),
    )
    auth_sessions = Table(
        'auth_sessions',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, nullable=False),
        Column('refresh_jti', String(64), nullable=False),
        Column('expires_at', DateTime, nullable=False),
        Column('created_at', DateTime, nullable=False),
    )
    metadata.create_all(migration_engine)
    identity_before = (7, 'Legacy User', 'legacy@example.com', 'BUYER', datetime(2026, 1, 1))

    with migration_engine.begin() as connection:
        connection.execute(users.insert().values(
            id=identity_before[0],
            company_name='Legacy Co',
            name=identity_before[1],
            email=identity_before[2],
            password='legacy-test-password',
            role=identity_before[3],
            created_at=identity_before[4],
        ))
        connection.execute(auth_sessions.insert().values(
            id=11,
            user_id=identity_before[0],
            refresh_jti='test-session-jti',
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            created_at=datetime.now(timezone.utc),
        ))

    assert migrate_legacy_passwords(migration_engine) == 1
    assert migrate_legacy_passwords(migration_engine) == 0

    migrated_users = Table('users', MetaData(), autoload_with=migration_engine)
    with migration_engine.connect() as connection:
        migrated = connection.execute(select(migrated_users)).mappings().one()
        session_count = connection.execute(select(auth_sessions.c.id)).all()

    assert 'password_hash' in {column['name'] for column in inspect(migration_engine).get_columns('users')}
    assert migrated['password'] == PASSWORD_DISABLED_VALUE
    assert migrated['password_hash'] != 'legacy-test-password'
    assert migrated['password_hash'].startswith('$argon2id$')
    assert verify_password('legacy-test-password', migrated['password_hash']) is True
    assert (migrated['id'], migrated['name'], migrated['email'], migrated['role'], migrated['created_at']) == identity_before
    assert len(session_count) == 1


def test_login_outcomes_jwt_contract_and_password_api_non_exposure(client):
    valid = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
    assert valid.status_code == 200
    login_payload = valid.json()

    assert client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'wrong'}).status_code == 401
    assert client.post('/auth/login', json={'email': 'missing@example.com', 'password': 'wrong'}).status_code == 401

    access_payload = jwt.decode(
        login_payload['access_token'],
        get_jwt_secret_key(),
        algorithms=[get_jwt_algorithm()],
    )
    assert access_payload['sub'] == str(login_payload['user_id'])
    assert access_payload['type'] == 'access'
    assert 'sid' in access_payload
    assert login_payload['role'] == 'BUYER'

    headers = {'Authorization': f"Bearer {login_payload['access_token']}"}
    responses = [
        client.get('/users'),
        client.get(f"/users/{login_payload['user_id']}"),
        client.get('/auth/me', headers=headers),
        client.get('/members/me', headers=headers),
    ]
    for response in responses:
        assert response.status_code == 200
        assert 'password' not in response.text.lower()

    openapi = client.get('/openapi.json')
    assert openapi.status_code == 200
    schemas = openapi.json()['components']['schemas']
    for schema_name in ['UserResponse', 'LoginResponse', 'MemberMeResponse']:
        properties = schemas[schema_name].get('properties', {})
        assert 'password' not in properties
        assert 'password_hash' not in properties


def test_auth_session_count_survives_failed_login(client):
    with SessionLocal() as db:
        before = db.query(AuthSession).count()

    assert client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'wrong'}).status_code == 401

    with SessionLocal() as db:
        assert db.query(AuthSession).count() == before