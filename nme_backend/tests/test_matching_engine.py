import threading

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Order, Product, Trade


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    return payload


def create_order(client, token, payload):
    headers = {'Authorization': f"Bearer {token}"}
    return client.post('/orders', json=payload, headers=headers)


def test_basic_buy_sell_match(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 2500, 'side': 'sell'},
    )
    assert sell_response.status_code == 200
    sell_order_id = sell_response.json()['id']

    buy_response = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 40, 'price': 2600, 'side': 'buy'},
    )
    assert buy_response.status_code == 200
    buy_order_id = buy_response.json()['id']

    match_response = client.post(f'/orders/{buy_order_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200
    body = match_response.json()
    assert body['matched_quantity'] == 40
    assert body['trade_count'] == 1

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_order_id).first()
        sell_order = db.query(Order).filter(Order.id == sell_order_id).first()
        trade = db.query(Trade).filter(Trade.buy_order_id == buy_order_id, Trade.sell_order_id == sell_order_id).first()
        product = db.query(Product).filter(Product.id == product_id).first()

        assert buy_order is not None and sell_order is not None and trade is not None
        assert buy_order.remaining_quantity == 0
        assert sell_order.remaining_quantity == 0
        assert trade.quantity == 40
        assert trade.product_id == product_id
        assert product.quantity == 100


def test_no_price_match(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': 2500, 'side': 'sell'},
    )
    buy_response = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 10, 'price': 2400, 'side': 'buy'},
    )

    assert sell_response.status_code == 200
    assert buy_response.status_code == 200

    match_response = client.post(f"/orders/{buy_response.json()['id']}/match", headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200
    assert match_response.json()['trade_count'] == 0

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_response.json()['id']).first()
        sell_order = db.query(Order).filter(Order.id == sell_response.json()['id']).first()
        assert buy_order is not None and sell_order is not None
        assert buy_order.remaining_quantity == 10
        assert sell_order.remaining_quantity == 10
        assert db.query(Trade).count() == 0


def test_partial_fill_and_remaining_quantity(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 2500, 'side': 'sell'},
    )
    buy_response = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 100, 'price': 2600, 'side': 'buy'},
    )

    match_response = client.post(f"/orders/{buy_response.json()['id']}/match", headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200
    body = match_response.json()
    assert body['matched_quantity'] == 40

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_response.json()['id']).first()
        sell_order = db.query(Order).filter(Order.id == sell_response.json()['id']).first()
        assert buy_order is not None and sell_order is not None
        assert buy_order.remaining_quantity == 60
        assert sell_order.remaining_quantity == 0
        assert db.query(Trade).count() == 1


def test_self_trade_prevented(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    order_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2500, 'side': 'sell'},
    )
    assert order_response.status_code == 200
    order_id = order_response.json()['id']

    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        assert order is not None
        order.buyer_id = seeded_ids['seller_id']
        order.side = 'buy'
        db.add(order)
        db.commit()

    match_response = client.post(f'/orders/{order_id}/match', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert match_response.status_code == 200
    assert match_response.json()['trade_count'] == 0

    with SessionLocal() as db:
        refreshed = db.query(Order).filter(Order.id == order_id).first()
        assert refreshed is not None
        assert refreshed.remaining_quantity == 20
        assert db.query(Trade).count() == 0


def test_fifo_priority_and_multi_trade(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_a = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2500, 'side': 'sell'},
    )
    sell_b = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 30, 'price': 2400, 'side': 'sell'},
    )
    sell_c = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 50, 'price': 2600, 'side': 'sell'},
    )

    assert sell_a.status_code == 200 and sell_b.status_code == 200 and sell_c.status_code == 200

    buy_response = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 100, 'price': 3000, 'side': 'buy'},
    )
    assert buy_response.status_code == 200
    buy_order_id = buy_response.json()['id']

    match_response = client.post(f'/orders/{buy_order_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert match_response.status_code == 200
    body = match_response.json()
    assert body['matched_quantity'] == 100
    assert body['trade_count'] == 3

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_order_id).first()
        assert buy_order is not None and buy_order.remaining_quantity == 0
        assert db.query(Trade).count() == 3


def test_concurrent_matching_does_not_overfill(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 100, 'price': 2500, 'side': 'sell'},
    )
    assert sell_response.status_code == 200
    sell_order_id = sell_response.json()['id']

    buy_a = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 60, 'price': 2600, 'side': 'buy'},
    )
    buy_b = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 60, 'price': 2600, 'side': 'buy'},
    )
    assert buy_a.status_code == 200 and buy_b.status_code == 200
    buy_ids = [buy_a.json()['id'], buy_b.json()['id']]

    results = []
    lock = threading.Lock()

    def run_match(order_id):
        response = client.post(f'/orders/{order_id}/match', headers={'Authorization': f"Bearer {buyer['access_token']}"})
        with lock:
            results.append((order_id, response.status_code, response.json()))

    threads = [threading.Thread(target=run_match, args=(order_id,)) for order_id in buy_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with SessionLocal() as db:
        sell_order = db.query(Order).filter(Order.id == sell_order_id).first()
        trades = db.query(Trade).filter(Trade.sell_order_id == sell_order_id).all()
        assert sell_order is not None
        assert sell_order.remaining_quantity >= 0
        total_trade_quantity = sum(trade.quantity for trade in trades)
        assert total_trade_quantity <= 100
        assert sum(response[2]['matched_quantity'] for response in results if response[1] == 200) <= 100
