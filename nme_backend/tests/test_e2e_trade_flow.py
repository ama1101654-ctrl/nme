from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    assert payload['refresh_token']
    assert payload['token_type'] == 'bearer'
    return payload


def test_database_isolation():
    from app.database import engine

    database_path = Path(engine.url.database).resolve()
    assert database_path.name != 'nme.db'
    assert 'nme-step49-' in database_path.as_posix()


def test_e2e_trade_flow_and_history_dashboard(client, seeded_ids):
    health = client.get('/health')
    assert health.status_code == 200
    assert health.json() == {'status': 'ok'}

    market = client.get('/market')
    assert market.status_code == 200
    market_data = market.json()
    assert isinstance(market_data, list)
    assert market_data

    available_product = next((item for item in market_data if item['status'] == 'available'), None)
    assert available_product is not None

    buyer = login(client, 'bob@example.com')
    buyer_me = client.get('/auth/me', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_me.status_code == 200
    buyer_me_data = buyer_me.json()
    assert buyer_me_data['role'] == 'BUYER'
    assert buyer_me_data['email'] == 'bob@example.com'

    buyer_sessions = client.get('/auth/sessions', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_sessions.status_code == 200
    buyer_sessions_data = buyer_sessions.json()
    assert isinstance(buyer_sessions_data, list)
    assert buyer_sessions_data
    assert any(session['is_current'] for session in buyer_sessions_data)

    seller = login(client, 'charlie@example.com')
    seller_me = client.get('/auth/me', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert seller_me.status_code == 200
    assert seller_me.json()['role'] == 'SELLER'

    product_id = available_product['product_id']
    buyer_id = seeded_ids['buyer_id']
    proposed_price = int(available_product['price'])
    quantity = 1

    deal_response = client.post(
        '/deals',
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
        json={
            'product_id': product_id,
            'buyer_id': buyer_id,
            'quantity': quantity,
            'proposed_price': proposed_price,
        },
    )
    assert deal_response.status_code == 200
    deal = deal_response.json()
    assert deal['id']
    assert deal['status'] == 'NEGOTIATING'

    agree_response = client.patch(
        f"/deals/{deal['id']}/status",
        headers={'Authorization': f"Bearer {seller['access_token']}"},
        json={'status': 'AGREED'},
    )
    assert agree_response.status_code == 200
    agreed_deal = agree_response.json()
    assert agreed_deal['status'] == 'AGREED'

    order_response = client.post(
        f"/deals/{deal['id']}/create-order",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert order_response.status_code == 200
    order = order_response.json()
    assert order['id']
    assert order['status'] == 'PENDING'
    assert order['product_id'] == product_id
    assert order['buyer_id'] == buyer_id

    next_statuses = ['ACCEPTED', 'PAID', 'SHIPPED', 'COMPLETED']
    current_order = order
    for next_status in next_statuses:
        status_response = client.patch(
            f"/orders/{current_order['id']}/status",
            headers={'Authorization': f"Bearer {buyer['access_token']}"},
            json={'status': next_status},
        )
        assert status_response.status_code == 200
        current_order = status_response.json()
        assert current_order['status'] == next_status

    completion_response = client.get(f"/deals/{deal['id']}/completion")
    assert completion_response.status_code == 200
    completion = completion_response.json()
    assert completion['deal_id'] == deal['id']
    assert completion['order_id'] == order['id']
    assert completion['status'] == 'COMPLETED'
    assert completion['completed'] is True

    history_response = client.get('/deals')
    assert history_response.status_code == 200
    history = history_response.json()
    assert isinstance(history, list)
    assert any(item['id'] == deal['id'] for item in history)

    deal_order_response = client.get(f"/deals/{deal['id']}/order")
    assert deal_order_response.status_code == 200
    deal_order = deal_order_response.json()
    assert deal_order['id'] == order['id']
    assert deal_order['status'] == 'COMPLETED'

    buyer_dashboard = client.get(f"/users/{buyer_id}")
    seller_dashboard = client.get(f"/users/{seeded_ids['seller_id']}")
    assert buyer_dashboard.status_code == 200
    assert seller_dashboard.status_code == 200
    assert buyer_dashboard.json()['role'] == 'BUYER'
    assert seller_dashboard.json()['role'] == 'SELLER'

    dashboard_market = client.get('/market')
    dashboard_deals = client.get('/deals')
    assert dashboard_market.status_code == 200
    assert dashboard_deals.status_code == 200
