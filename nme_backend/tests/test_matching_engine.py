import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def test_matching_returns_persisted_trade_id_with_existing_trade(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    with SessionLocal() as db:
        existing_buy = Order(
            product_id=product_id,
            buyer_id=seeded_ids['buyer_id'],
            quantity=1,
            remaining_quantity=0,
            price=2400,
            side='buy',
            status='FILLED',
        )
        existing_sell = Order(
            product_id=product_id,
            seller_id=seeded_ids['seller_id'],
            quantity=1,
            remaining_quantity=0,
            price=2400,
            side='sell',
            status='FILLED',
        )
        db.add_all([existing_buy, existing_sell])
        db.flush()
        existing_trade = Trade(
            product_id=product_id,
            buy_order_id=existing_buy.id,
            sell_order_id=existing_sell.id,
            quantity=1,
            price=2400,
        )
        db.add(existing_trade)
        db.commit()
        existing_trade_id = existing_trade.id

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': 2500, 'side': 'sell'},
    )
    buy_response = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 10, 'price': 2600, 'side': 'buy'},
    )
    assert sell_response.status_code == 200 and buy_response.status_code == 200

    match_response = client.post(
        f"/orders/{buy_response.json()['id']}/match",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert match_response.status_code == 200
    body = match_response.json()
    assert body['trade_count'] == 1

    with SessionLocal() as db:
        matched_trade = db.query(Trade).filter(
            Trade.buy_order_id == buy_response.json()['id'],
            Trade.sell_order_id == sell_response.json()['id'],
        ).one()
        assert matched_trade.id != existing_trade_id
        assert body['trades'][0]['trade_id'] == matched_trade.id

    trade_id = body['trades'][0]['trade_id']
    detail_response = client.get(f'/trades/{trade_id}')
    assert detail_response.status_code == 200
    assert detail_response.json()['trade_id'] == trade_id

    contract_response = client.post(
        f'/trades/{trade_id}/contract',
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert contract_response.status_code == 200
    assert contract_response.json()['trade_id'] == trade_id


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
        assert body['trades'][0]['trade_id'] == trade.id


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
        trade = db.query(Trade).one()
        assert body['trades'][0]['trade_id'] == trade.id


def test_self_trade_prevented(client, seeded_ids):
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2500, 'side': 'sell'},
    )
    buy_response = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2600, 'side': 'buy'},
    )
    assert sell_response.status_code == 200
    assert buy_response.status_code == 200
    buy_order_id = buy_response.json()['id']

    match_response = client.post(f'/orders/{buy_order_id}/match', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert match_response.status_code == 200
    assert match_response.json()['trade_count'] == 0

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_order_id).one()
        sell_order = db.query(Order).filter(Order.id == sell_response.json()['id']).one()
        assert buy_order.remaining_quantity == 20
        assert sell_order.remaining_quantity == 20
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
        trades = db.query(Trade).filter(Trade.buy_order_id == buy_order_id).order_by(Trade.id.asc()).all()
        assert buy_order is not None and buy_order.remaining_quantity == 0
        assert len(trades) == 3
        assert [trade.sell_order_id for trade in trades] == [sell_b.json()['id'], sell_a.json()['id'], sell_c.json()['id']]
        for trade_payload in body['trades']:
            trade = db.query(Trade).filter(Trade.id == trade_payload['trade_id']).one()
            assert trade.buy_order_id == trade_payload['buy_order_id']
            assert trade.sell_order_id == trade_payload['sell_order_id']
            assert trade.quantity == trade_payload['quantity']
            assert trade.price == trade_payload['price']


def test_repeated_matching_returns_distinct_persisted_trade_ids(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 20, 'price': 2600, 'side': 'buy'},
    )
    assert buy.status_code == 200

    returned_trade_ids = []
    sell_order_ids = []
    for price in (2500, 2400):
        sell = create_order(
            client,
            seller['access_token'],
            {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 10, 'price': price, 'side': 'sell'},
        )
        assert sell.status_code == 200
        sell_order_ids.append(sell.json()['id'])

        response = client.post(
            f"/orders/{buy.json()['id']}/match",
            headers={'Authorization': f"Bearer {buyer['access_token']}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body['trade_count'] == 1
        returned_trade_ids.append(body['trades'][0]['trade_id'])

    assert len(set(returned_trade_ids)) == 2
    with SessionLocal() as db:
        for trade_id, sell_order_id in zip(returned_trade_ids, sell_order_ids):
            trade = db.query(Trade).filter(Trade.id == trade_id).one()
            assert trade.buy_order_id == buy.json()['id']
            assert trade.sell_order_id == sell_order_id


def test_same_price_fifo_uses_order_id_as_tiebreaker(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell_a = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2400, 'side': 'sell'},
    )
    sell_b = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2400, 'side': 'sell'},
    )
    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 20, 'price': 2500, 'side': 'buy'},
    )
    assert sell_a.status_code == 200 and sell_b.status_code == 200 and buy.status_code == 200

    response = client.post(
        f"/orders/{buy.json()['id']}/match",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        trade = db.query(Trade).filter(Trade.buy_order_id == buy.json()['id']).one()
        assert trade.sell_order_id == sell_a.json()['id']


def test_matching_isolated_by_product(client, seeded_ids):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')

    with SessionLocal() as db:
        other_product = Product(
            seller_id=seeded_ids['seller_id'],
            metal='Copper',
            grade='C1020',
            quantity=100,
            unit='TON',
            price=2400,
            status='available',
        )
        db.add(other_product)
        db.commit()
        db.refresh(other_product)
        other_product_id = other_product.id

    sell = create_order(
        client,
        seller['access_token'],
        {'product_id': other_product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 20, 'price': 2400, 'side': 'sell'},
    )
    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': seeded_ids['product_id'], 'buyer_id': seeded_ids['buyer_id'], 'quantity': 20, 'price': 2500, 'side': 'buy'},
    )
    assert sell.status_code == 200 and buy.status_code == 200

    response = client.post(
        f"/orders/{buy.json()['id']}/match",
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()['matched_quantity'] == 0
    assert response.json()['trade_count'] == 0


def test_matching_rolls_back_after_trade_flush_failure(client, seeded_ids, monkeypatch):
    buyer = login(client, 'bob@example.com')
    seller = login(client, 'charlie@example.com')
    product_id = seeded_ids['product_id']

    sell = create_order(
        client,
        seller['access_token'],
        {'product_id': product_id, 'seller_id': seeded_ids['seller_id'], 'quantity': 40, 'price': 2400, 'side': 'sell'},
    )
    buy = create_order(
        client,
        buyer['access_token'],
        {'product_id': product_id, 'buyer_id': seeded_ids['buyer_id'], 'quantity': 40, 'price': 2500, 'side': 'buy'},
    )
    assert sell.status_code == 200 and buy.status_code == 200

    original_flush = Session.flush

    def fail_after_trade_flush(session, objects=None):
        has_pending_trade = any(isinstance(item, Trade) for item in session.new)
        original_flush(session, objects)
        if has_pending_trade:
            raise RuntimeError('intentional matching rollback audit failure')

    monkeypatch.setattr(Session, 'flush', fail_after_trade_flush)
    with pytest.raises(RuntimeError, match='intentional matching rollback audit failure'):
        client.post(
            f"/orders/{buy.json()['id']}/match",
            headers={'Authorization': f"Bearer {buyer['access_token']}"},
        )

    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy.json()['id']).one()
        sell_order = db.query(Order).filter(Order.id == sell.json()['id']).one()
        assert buy_order.remaining_quantity == 40
        assert sell_order.remaining_quantity == 40
        assert buy_order.status == 'PENDING'
        assert sell_order.status == 'PENDING'
        assert db.query(Trade).count() == 0


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
