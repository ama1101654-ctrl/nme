from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.database import SessionLocal
from app.main import get_jwt_algorithm, get_jwt_secret_key
from app.models import Order, Product


pytestmark = pytest.mark.security


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    assert payload['refresh_token']
    return payload


def test_login_me_sessions_refresh_logout_rotation(client):
    buyer = login(client, 'bob@example.com')

    buyer_me = client.get('/auth/me', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_me.status_code == 200
    assert buyer_me.json()['role'] == 'BUYER'

    buyer_sessions = client.get('/auth/sessions', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_sessions.status_code == 200
    buyer_sessions_data = buyer_sessions.json()
    assert isinstance(buyer_sessions_data, list)
    assert any(session['is_current'] for session in buyer_sessions_data)

    rotated = client.post('/auth/refresh', json={'refresh_token': buyer['refresh_token']})
    assert rotated.status_code == 200
    rotated_payload = rotated.json()
    assert rotated_payload['access_token']
    assert rotated_payload['refresh_token']

    old_refresh_reuse = client.post('/auth/refresh', json={'refresh_token': buyer['refresh_token']})
    assert old_refresh_reuse.status_code == 401

    logout_response = client.post(
        '/auth/logout',
        headers={'Authorization': f"Bearer {rotated_payload['access_token']}"},
        json={'refresh_token': rotated_payload['refresh_token']},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()['status'] == 'logged_out'

    logout_refresh_reuse = client.post('/auth/refresh', json={'refresh_token': rotated_payload['refresh_token']})
    assert logout_refresh_reuse.status_code == 401


def test_seller_session_ownership_and_revoke_all(client):
    buyer = login(client, 'bob@example.com')
    buyer_sessions = client.get('/auth/sessions', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_sessions.status_code == 200
    buyer_session_id = buyer_sessions.json()[0]['id']

    seller = login(client, 'charlie@example.com')
    seller_me = client.get('/auth/me', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert seller_me.status_code == 200
    assert seller_me.json()['role'] == 'SELLER'

    revoke_attempt = client.post(
        f'/auth/sessions/{buyer_session_id}/revoke',
        headers={'Authorization': f"Bearer {seller['access_token']}"},
    )
    assert revoke_attempt.status_code == 404

    revoke_all = client.post(
        '/auth/sessions/revoke-all',
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert revoke_all.status_code == 200
    assert revoke_all.json()['status'] == 'all_sessions_revoked'


def test_order_and_deal_creation_enforces_authenticated_buyer(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    auth_headers = {'Authorization': f"Bearer {buyer['access_token']}"}
    product_id = seeded_ids['product_id']
    price = seeded_ids['product_price']

    missing_auth_order = client.post('/orders', json={'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 1, 'price': price})
    assert missing_auth_order.status_code == 401

    mismatched_order = client.post(
        '/orders',
        json={'product_id': product_id, 'buyer_id': seeded_ids['seller_id'], 'quantity': 1, 'price': price},
        headers=auth_headers,
    )
    assert mismatched_order.status_code == 403

    valid_order = client.post(
        '/orders',
        json={'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 1, 'price': price},
        headers=auth_headers,
    )
    assert valid_order.status_code == 200
    assert valid_order.json()['buyer_id'] == seeded_ids['buyer_id']

    missing_auth_deal = client.post('/deals', json={'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 1, 'proposed_price': price})
    assert missing_auth_deal.status_code == 401

    mismatched_deal = client.post(
        '/deals',
        json={'product_id': product_id, 'buyer_id': seeded_ids['seller_id'], 'quantity': 1, 'proposed_price': price},
        headers=auth_headers,
    )
    assert mismatched_deal.status_code == 403

    valid_deal = client.post(
        '/deals',
        json={'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 1, 'proposed_price': price},
        headers=auth_headers,
    )
    assert valid_deal.status_code == 200
    assert valid_deal.json()['buyer_id'] == seeded_ids['buyer_id']


def test_sell_order_creation_uses_authenticated_seller_identity(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    auth_headers = {'Authorization': f"Bearer {seller['access_token']}"}
    product_id = seeded_ids['product_id']
    price = seeded_ids['product_price']

    mismatched_sell_order = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['buyer_id'], 'quantity': 1, 'price': price, 'side': 'sell'},
        headers=auth_headers,
    )
    assert mismatched_sell_order.status_code == 403

    valid_sell_order = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 1, 'price': price, 'side': 'sell'},
        headers=auth_headers,
    )
    assert valid_sell_order.status_code == 200
    payload = valid_sell_order.json()
    assert payload['seller_id'] == seeded_ids['seller_id']
    assert payload['side'] == 'sell'
    assert payload['buyer_id'] is None


def test_order_creation_infers_authenticated_identity(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']
    price = seeded_ids['product_price']

    unauthenticated_sell = client.post(
        '/orders',
        json={'product_id': product_id, 'quantity': 1, 'price': price, 'side': 'sell'},
    )
    assert unauthenticated_sell.status_code == 401

    buy_response = client.post(
        '/orders',
        json={'product_id': product_id, 'quantity': 2, 'price': price, 'side': 'buy'},
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert buy_response.status_code == 200
    assert buy_response.json()['buyer_id'] == seeded_ids['buyer_id']

    sell_response = client.post(
        '/orders',
        json={'product_id': product_id, 'quantity': 3, 'price': price, 'side': 'sell'},
        headers={'Authorization': f"Bearer {seller['access_token']}"},
    )
    assert sell_response.status_code == 200
    assert sell_response.json()['seller_id'] == seeded_ids['seller_id']


def test_deal_and_order_mutations_require_expected_owner(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    admin = login(client, 'alice@example.com')
    buyer_headers = {'Authorization': f"Bearer {buyer['access_token']}"}
    seller_headers = {'Authorization': f"Bearer {seller['access_token']}"}
    admin_headers = {'Authorization': f"Bearer {admin['access_token']}"}

    deal_response = client.post(
        '/deals',
        json={
            'product_id': seeded_ids['product_id'],
            'buyer_id': seeded_ids['buyer_id'],
            'quantity': 2,
            'proposed_price': seeded_ids['product_price'],
        },
        headers=buyer_headers,
    )
    assert deal_response.status_code == 200
    deal_id = deal_response.json()['id']

    assert client.patch(f'/deals/{deal_id}/status', json={'status': 'AGREED'}).status_code == 401
    assert client.patch(f'/deals/{deal_id}/status', json={'status': 'AGREED'}, headers=admin_headers).status_code == 403
    assert client.patch(f'/deals/{deal_id}/status', json={'status': 'NEGOTIATING'}, headers=admin_headers).status_code == 403
    assert client.patch(f'/deals/{deal_id}/status', json={'status': 'AGREED'}, headers=buyer_headers).status_code == 403

    agreed = client.patch(f'/deals/{deal_id}/status', json={'status': 'AGREED'}, headers=seller_headers)
    assert agreed.status_code == 200

    assert client.post(f'/deals/{deal_id}/create-order').status_code == 401
    assert client.post(f'/deals/{deal_id}/create-order', headers=seller_headers).status_code == 403

    order_response = client.post(f'/deals/{deal_id}/create-order', headers=buyer_headers)
    assert order_response.status_code == 200
    order_id = order_response.json()['id']

    assert client.patch(f'/orders/{order_id}/status', json={'status': 'ACCEPTED'}).status_code == 401
    assert client.patch(f'/orders/{order_id}/status', json={'status': 'ACCEPTED'}, headers=seller_headers).status_code == 403
    accepted = client.patch(f'/orders/{order_id}/status', json={'status': 'ACCEPTED'}, headers=buyer_headers)
    assert accepted.status_code == 200
    assert accepted.json()['status'] == 'ACCEPTED'


def test_match_requires_authentication_and_order_ownership(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    buyer_headers = {'Authorization': f"Bearer {buyer['access_token']}"}
    seller_headers = {'Authorization': f"Bearer {seller['access_token']}"}
    order_payload = {
        'product_id': seeded_ids['product_id'],
        'quantity': 5,
        'price': seeded_ids['product_price'],
    }

    sell_response = client.post('/orders', json={**order_payload, 'side': 'sell'}, headers=seller_headers)
    buy_response = client.post('/orders', json={**order_payload, 'side': 'buy'}, headers=buyer_headers)
    assert sell_response.status_code == 200
    assert buy_response.status_code == 200
    buy_order_id = buy_response.json()['id']

    assert client.post(f'/orders/{buy_order_id}/match').status_code == 401
    assert client.post(f'/orders/{buy_order_id}/match', headers=seller_headers).status_code == 403

    matched = client.post(f'/orders/{buy_order_id}/match', headers=buyer_headers)
    assert matched.status_code == 200
    assert matched.json()['matched_quantity'] == 5

    filled_status_change = client.patch(
        f'/orders/{buy_order_id}/status',
        json={'status': 'CANCELLED'},
        headers=buyer_headers,
    )
    assert filled_status_change.status_code == 400

    with SessionLocal() as db:
        filled_order = db.query(Order).filter(Order.id == buy_order_id).one()
        assert filled_order.status == 'FILLED'
        assert filled_order.remaining_quantity == 0


def test_product_creation_requires_authenticated_seller_identity(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    payload = {
        'seller_id': seeded_ids['seller_id'],
        'metal': 'Copper',
        'grade': 'C1100',
        'quantity': 10,
        'unit': 'TON',
        'price': 1000,
        'status': 'available',
    }

    assert client.post('/products', json=payload).status_code == 401
    assert client.post('/products', json=payload, headers={'Authorization': f"Bearer {buyer['access_token']}"}).status_code == 403

    spoofed = client.post(
        '/products',
        json={**payload, 'seller_id': seeded_ids['buyer_id']},
        headers={'Authorization': f"Bearer {seller['access_token']}"},
    )
    assert spoofed.status_code == 403

    created = client.post('/products', json=payload, headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert created.status_code == 200
    assert created.json()['seller_id'] == seeded_ids['seller_id']


def test_invalid_and_expired_access_tokens_are_rejected(client, seeded_ids):
    invalid = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'quantity': 1, 'price': 1000, 'side': 'buy'},
        headers={'Authorization': 'Bearer invalid-token'},
    )
    assert invalid.status_code == 401

    expired_token = jwt.encode(
        {
            'sub': str(seeded_ids['buyer_id']),
            'type': 'access',
            'exp': datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        get_jwt_secret_key(),
        algorithm=get_jwt_algorithm(),
    )
    expired = client.post(
        '/orders',
        json={'product_id': seeded_ids['product_id'], 'quantity': 1, 'price': 1000, 'side': 'buy'},
        headers={'Authorization': f'Bearer {expired_token}'},
    )
    assert expired.status_code == 401


def test_public_signup_cannot_assign_privileged_role(client):
    response = client.post(
        '/users',
        json={
            'company_name': 'Example',
            'name': 'Public User',
            'email': 'public@example.com',
            'password': 'secret',
            'role': 'ADMIN',
        },
    )
    assert response.status_code == 200
    assert response.json()['role'] == 'USER'


def test_item_mutation_requires_admin(client):
    buyer = login(client, 'bob@example.com')
    admin = login(client, 'alice@example.com')
    payload = {'name': 'Audit item', 'description': 'Temporary DB only'}

    assert client.post('/items', json=payload).status_code == 401
    forbidden = client.post(
        '/items',
        json=payload,
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert forbidden.status_code == 403

    created = client.post(
        '/items',
        json=payload,
        headers={'Authorization': f"Bearer {admin['access_token']}"},
    )
    assert created.status_code == 200


def test_sell_order_validates_side_quantity_and_product_inventory(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    auth_headers = {'Authorization': f"Bearer {seller['access_token']}"}
    product_id = seeded_ids['product_id']
    price = seeded_ids['product_price']

    oversize_sell = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 101, 'price': price, 'side': 'SELL'},
        headers=auth_headers,
    )
    assert oversize_sell.status_code == 409
    assert oversize_sell.json()['detail'] == 'Insufficient available inventory for sell order'

    buyer_contained_sell = client.post(
        '/orders',
        json={'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'seller_id': seeded_ids['seller_id'], 'quantity': 5, 'price': price, 'side': 'SELL'},
        headers=auth_headers,
    )
    assert buyer_contained_sell.status_code in {400, 422}

    non_positive_quantity = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 0, 'price': price, 'side': 'sell'},
        headers=auth_headers,
    )
    assert non_positive_quantity.status_code in {400, 422}

    non_positive_price = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 5, 'price': 0, 'side': 'sell'},
        headers=auth_headers,
    )
    assert non_positive_price.status_code in {400, 422}

    valid_sell_with_uppercase_side = client.post(
        '/orders',
        json={'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': price, 'side': 'SELL'},
        headers=auth_headers,
    )
    assert valid_sell_with_uppercase_side.status_code in {200, 201}
    payload = valid_sell_with_uppercase_side.json()
    assert payload['buyer_id'] is None
    assert payload['seller_id'] == seeded_ids['seller_id']
    assert payload['side'] == 'sell'

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        assert product is not None
        assert product.quantity == 100


def test_cors_regression(client):
    allowed_localhost = client.get('/market', headers={'Origin': 'http://localhost:5174'})
    allowed_loopback = client.get('/market', headers={'Origin': 'http://127.0.0.1:5174'})
    denied_evil = client.get('/market', headers={'Origin': 'http://evil.example.com'})
    assert allowed_localhost.status_code == 200
    assert allowed_localhost.headers.get('access-control-allow-origin') == 'http://localhost:5174'
    assert allowed_loopback.status_code == 200
    assert allowed_loopback.headers.get('access-control-allow-origin') == 'http://127.0.0.1:5174'
    assert denied_evil.status_code == 200
    assert denied_evil.headers.get('access-control-allow-origin') is None


def test_rate_limit_regression(client):
    for _ in range(10):
        response = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
        assert response.status_code == 200

    rate_limit_response = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
    assert rate_limit_response.status_code == 429

    # Use a fresh client fixture in a new test invocation for refresh regression.
    # The login bucket is intentionally isolated per test case by conftest.


def test_refresh_rate_limit_regression(client):
    buyer = login(client, 'bob@example.com')
    refresh_token = buyer['refresh_token']
    for _ in range(30):
        response = client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert response.status_code == 200
        payload = response.json()
        assert payload['access_token']
        assert payload['refresh_token']
        refresh_token = payload['refresh_token']

    refresh_rate_limit_response = client.post('/auth/refresh', json={'refresh_token': refresh_token})
    assert refresh_rate_limit_response.status_code == 429
