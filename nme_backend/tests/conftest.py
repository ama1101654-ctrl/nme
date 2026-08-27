import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix='nme-step49-'))
TEST_DB_PATH = TEST_DB_DIR / 'nme_test.db'
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB_PATH.as_posix()}'

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app, auth_login_rate_limiter, auth_refresh_rate_limiter  # noqa: E402
from app.models import AuthSession, Deal, Order, Product, User  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.query(AuthSession).delete(synchronize_session=False)
        db.query(Order).delete(synchronize_session=False)
        db.query(Deal).delete(synchronize_session=False)
        db.query(Product).delete(synchronize_session=False)
        db.query(User).delete(synchronize_session=False)
        db.commit()

        buyer = User(
            company_name='Acme',
            name='MVP Buyer',
            email='bob@example.com',
            password='secret',
            role='BUYER',
        )
        seller = User(
            company_name='Acme',
            name='MVP Seller',
            email='charlie@example.com',
            password='secret',
            role='SELLER',
        )
        admin = User(
            company_name='Acme',
            name='MVP Admin',
            email='alice@example.com',
            password='secret',
            role='ADMIN',
        )
        db.add_all([buyer, seller, admin])
        db.commit()
        db.refresh(buyer)
        db.refresh(seller)

        product = Product(
            seller_id=seller.id,
            metal='Aluminum',
            grade='A1050',
            quantity=100,
            unit='TON',
            price=3200000,
            status='available',
        )
        db.add(product)
        db.commit()

    auth_login_rate_limiter._buckets.clear()
    auth_refresh_rate_limiter._buckets.clear()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def seeded_ids():
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == 'bob@example.com').first()
        seller = db.query(User).filter(User.email == 'charlie@example.com').first()
        product = db.query(Product).order_by(Product.id.asc()).first()
        assert buyer is not None
        assert seller is not None
        assert product is not None
        return {
            'buyer_id': buyer.id,
            'seller_id': seller.id,
            'product_id': product.id,
            'product_price': product.price,
        }
