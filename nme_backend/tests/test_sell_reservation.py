import pytest

from app.database import SessionLocal
from app.models import Product


pytestmark = pytest.mark.security


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    assert payload['refresh_token']
    return payload


def test_sell_reservation_success(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    resp = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 1000, 'side': 'SELL'},
        headers=headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body['side'] == 'sell'
    assert body['seller_id'] == seeded_ids['seller_id']
    assert body['buyer_id'] is None
    assert body['remaining_quantity'] == 30

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.quantity == 100
        assert product.reserved_quantity == 30


def test_sell_reservation_accumulates(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    first = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    second = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 50, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.quantity == 100
        assert product.reserved_quantity == 80


def test_sell_oversell_rejected(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    auth_headers = {'Authorization': f"Bearer {seller['access_token']}"}

    first = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 60, 'price': 1000, 'side': 'sell'},
        headers=auth_headers,
    )
    assert first.status_code == 200

    oversell = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 41, 'price': 1000, 'side': 'sell'},
        headers=auth_headers,
    )

    assert oversell.status_code == 409
    assert 'Insufficient available inventory for sell order' in oversell.json()['detail']

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.quantity == 100
        assert product.reserved_quantity == 60


def test_sell_exact_remaining_inventory(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    first = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 60, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    second = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()['remaining_quantity'] == 60
    assert second.status_code == 200
    assert second.json()['remaining_quantity'] == 40

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.quantity == 100
        assert product.reserved_quantity == 100

    over_just_one = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 1, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    assert over_just_one.status_code == 409

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.reserved_quantity == 100


def test_sell_zero_quantity_and_negative_quantity_rejected(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    zero = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 0, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    negative = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': -5, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert zero.status_code in {400, 422}
    assert negative.status_code in {400, 422}


def test_sell_zero_price_and_negative_price_rejected(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    zero_price = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': 0, 'side': 'sell'},
        headers=headers,
    )
    negative_price = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': -5, 'side': 'sell'},
        headers=headers,
    )

    assert zero_price.status_code in {400, 422}
    assert negative_price.status_code in {400, 422}


def test_sell_product_ownership_rejected(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    headers = {'Authorization': f"Bearer {buyer['access_token']}"}

    resp = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert resp.status_code == 403


def test_sell_seller_spoofing_rejected(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    resp = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['buyer_id'], 'quantity': 10, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert resp.status_code == 403


def test_sell_buyer_id_rejected(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    resp = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'buyer_id': seeded_ids['buyer_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert resp.status_code in {400, 422}


def test_product_quantity_unchanged_after_sell(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    resp = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 25, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )

    assert resp.status_code == 200

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        assert product is not None
        assert product.quantity == 100
        assert product.reserved_quantity == 25


def test_failed_oversell_does_not_change_reserved_quantity_or_create_order(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    headers = {'Authorization': f"Bearer {seller['access_token']}"}

    initial = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    assert initial.status_code == 200

    oversell = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 61, 'price': 1000, 'side': 'sell'},
        headers=headers,
    )
    assert oversell.status_code == 409

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == seeded_ids['product_id']).first()
        order_count = db.query(__import__('app.models', fromlist=['Order']).Order).count()
        assert product is not None
        assert product.reserved_quantity == 40
        assert order_count == 1
