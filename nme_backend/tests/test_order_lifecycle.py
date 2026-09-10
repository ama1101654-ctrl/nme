from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Order, Product, Trade


def login(client: TestClient, email: str):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    return payload


def create_order(client: TestClient, token: str, payload):
    headers = {'Authorization': f'Bearer {token}'}
    return client.post('/orders', json=payload, headers=headers)


def test_order_lifecycle_and_trade_sum_invariant(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_a = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 2500, 'side': 'sell'},
    )
    sell_b = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 2500, 'side': 'sell'},
    )
    sell_c = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 2500, 'side': 'sell'},
    )

    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 100, 'price': 2600, 'side': 'buy'},
    )
    assert buy.status_code == 200
    buy_order_id = buy.json()['id']

    match_response = client.post(f'/orders/{buy_order_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200
    payload = match_response.json()
    assert payload['matched_quantity'] == 100

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_order_id).first()
        assert buy_order is not None
        assert buy_order.remaining_quantity == 0
        assert buy_order.status == 'FILLED'

        trades = db.query(Trade).filter(Trade.buy_order_id == buy_order_id).all()
        assert len(trades) == 3
        assert sum(trade.quantity for trade in trades) == 100
        assert buy_order.quantity == sum(trade.quantity for trade in trades) + buy_order.remaining_quantity


def test_filled_order_rematch_is_rejected(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 50, 'price': 2500, 'side': 'sell'},
    )
    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 50, 'price': 2600, 'side': 'buy'},
    )
    assert sell.status_code == 200 and buy.status_code == 200
    buy_id = buy.json()['id']

    first_match = client.post(f'/orders/{buy_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert first_match.status_code == 200
    assert first_match.json()['matched_quantity'] == 50

    second_match = client.post(f'/orders/{buy_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert second_match.status_code == 409

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == buy_id).first()
        assert order is not None
        assert order.remaining_quantity == 0
        assert order.status == 'FILLED'
        assert db.query(Trade).count() == 1


def test_trade_history_endpoints_only_return_related_records(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 2500, 'side': 'sell'},
    )
    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 30, 'price': 2600, 'side': 'buy'},
    )
    assert sell.status_code == 200 and buy.status_code == 200
    buy_order_id = buy.json()['id']

    match_response = client.post(f'/orders/{buy_order_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200

    order_trades = client.get(f'/orders/{buy_order_id}/trades', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert order_trades.status_code == 200
    order_payload = order_trades.json()
    assert len(order_payload) == 1
    assert order_payload[0]['buy_order_id'] == buy_order_id

    forbidden_trades = client.get(f'/orders/{buy_order_id}/trades', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert forbidden_trades.status_code == 403

    unauthorized_trades = client.get(f'/orders/{buy_order_id}/trades')
    assert unauthorized_trades.status_code == 401

    product_trades = client.get(f'/products/{product_id}/trades')
    assert product_trades.status_code == 200
    assert len(product_trades.json()) == 1

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == buy_order_id).first()
        product = db.query(Product).filter(Product.id == product_id).first()
        assert order is not None and product is not None
        assert order.remaining_quantity == 0
        assert product.quantity == 100


def test_public_trade_history_endpoint_returns_latest_trades(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_order_a = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2500, 'side': 'sell'},
    )
    sell_order_b = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 2510, 'side': 'sell'},
    )
    assert sell_order_a.status_code == 200 and sell_order_b.status_code == 200

    buy_order_a = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 20, 'price': 2600, 'side': 'buy'},
    )
    buy_order_b = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 30, 'price': 2610, 'side': 'buy'},
    )
    assert buy_order_a.status_code == 200 and buy_order_b.status_code == 200

    match_response_a = client.post(f"/orders/{buy_order_a.json()['id']}/match", headers={'Authorization': f"Bearer {buyer['access_token']}"})
    match_response_b = client.post(f"/orders/{buy_order_b.json()['id']}/match", headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response_a.status_code == 200
    assert match_response_b.status_code == 200

    response = client.get('/trades?limit=10')
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]['trade_id'] > payload[1]['trade_id']
    assert payload[0]['product_id'] == product_id
    assert payload[0]['side'] in {'buy', 'sell'}
    assert payload[0]['quantity'] > 0
    assert payload[0]['price'] > 0
    assert 'time' in payload[0]

    product_response = client.get(f'/products/{product_id}/trades?limit=10')
    assert product_response.status_code == 200
    product_payload = product_response.json()
    assert len(product_payload) == 2
    assert product_payload[0]['trade_id'] >= product_payload[1]['trade_id']
