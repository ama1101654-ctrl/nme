from pathlib import Path

import pytest

from app.database import SessionLocal
from app.models import Order, Product, Trade


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


def test_e2e_matching_history_summary_and_websockets(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = client.post(
        '/orders',
        headers={'Authorization': f"Bearer {seller['access_token']}"},
        json={
            'product_id': product_id,
            'seller_id': seeded_ids['seller_id'],
            'quantity': 40,
            'price': 2400,
            'side': 'sell',
        },
    )
    assert sell_response.status_code == 200
    sell_order = sell_response.json()

    with SessionLocal() as db:
        product = db.query(Product).filter(Product.id == product_id).one()
        assert product.quantity == 100
        assert product.reserved_quantity == 40

    buy_response = client.post(
        '/orders',
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
        json={
            'product_id': product_id,
            'buyer_id': seeded_ids['buyer_id'],
            'quantity': 40,
            'price': 2500,
            'side': 'buy',
        },
    )
    assert buy_response.status_code == 200
    buy_order = buy_response.json()
    assert buy_order['remaining_quantity'] == 40

    match_response = client.post(
        f"/orders/{buy_order['id']}/match",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert match_response.status_code == 200
    assert match_response.json()['matched_quantity'] == 40

    with SessionLocal() as db:
        trade = db.query(Trade).filter(Trade.buy_order_id == buy_order['id']).one()
        trade_id = trade.id
        matched_buy = db.query(Order).filter(Order.id == buy_order['id']).one()
        matched_sell = db.query(Order).filter(Order.id == sell_order['id']).one()
        product = db.query(Product).filter(Product.id == product_id).one()
        assert matched_buy.remaining_quantity == 0 and matched_buy.status == 'FILLED'
        assert matched_sell.remaining_quantity == 0 and matched_sell.status == 'FILLED'
        assert matched_buy.quantity == trade.quantity + matched_buy.remaining_quantity
        assert matched_sell.quantity == trade.quantity + matched_sell.remaining_quantity
        assert product.quantity == 100
        assert product.reserved_quantity == 40

    order_history = client.get(
        f"/orders/{buy_order['id']}/trades",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    product_history = client.get(f'/products/{product_id}/trades')
    public_history = client.get('/trades')
    detail = client.get(f'/trades/{trade_id}')
    summary = client.get(f'/products/{product_id}/market-summary')

    assert order_history.status_code == 200 and order_history.json()[0]['trade_id'] == trade_id
    assert product_history.status_code == 200 and product_history.json()[0]['trade_id'] == trade_id
    assert public_history.status_code == 200 and public_history.json()[0]['trade_id'] == trade_id
    assert detail.status_code == 200
    assert detail.json()['trade_id'] == trade_id
    assert detail.json()['product_id'] == product_id
    assert detail.json()['quantity'] == 40
    assert detail.json()['price'] == 2400
    assert summary.status_code == 200
    assert summary.json()['trade_count'] == 1
    assert summary.json()['total_quantity'] == 40
    assert summary.json()['total_value'] == 96000
    assert summary.json()['average_price'] == 2400

    with client.websocket_connect('/ws/orderbook') as websocket:
        orderbook = websocket.receive_json()
        assert all(level['price'] != 2500 for level in orderbook['bids'])
        assert all(level['price'] != 2400 for level in orderbook['asks'])

    with client.websocket_connect('/ws/trades') as websocket:
        trade_event = websocket.receive_json()
        assert trade_event['trade_id'] == trade_id
        assert trade_event['product_id'] == product_id
        assert trade_event['quantity'] == 40
        assert trade_event['price'] == 2400
