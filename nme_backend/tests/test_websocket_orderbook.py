from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Order, Product, User


def test_ws_orderbook_uses_remaining_quantity_and_active_orders():
    with SessionLocal() as db:
        buyer = User(
            company_name='Acme',
            name='Orderbook Buyer',
            email='orderbook-buyer@example.com',
            password='secret',
            role='BUYER',
        )
        seller = User(
            company_name='Acme',
            name='Orderbook Seller',
            email='orderbook-seller@example.com',
            password='secret',
            role='SELLER',
        )
        db.add_all([buyer, seller])
        db.commit(); db.refresh(buyer); db.refresh(seller)

        product = Product(
            seller_id=seller.id,
            metal='Copper',
            grade='CATH',
            quantity=200,
            unit='TON',
            price=101.0,
            status='available',
        )
        db.add(product)
        db.commit(); db.refresh(product)

        active_buy = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=80,
            remaining_quantity=80,
            price=100.0,
            side='buy',
            status='PENDING',
        )
        partial_buy = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=100,
            remaining_quantity=60,
            price=99.0,
            side='buy',
            status='PARTIAL',
        )
        filled_buy = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=50,
            remaining_quantity=0,
            price=98.0,
            side='buy',
            status='FILLED',
        )
        active_sell = Order(
            product_id=product.id,
            seller_id=seller.id,
            quantity=70,
            remaining_quantity=70,
            price=102.0,
            side='sell',
            status='PENDING',
        )
        partial_sell = Order(
            product_id=product.id,
            seller_id=seller.id,
            quantity=90,
            remaining_quantity=60,
            price=103.0,
            side='sell',
            status='PARTIAL',
        )
        filled_sell = Order(
            product_id=product.id,
            seller_id=seller.id,
            quantity=40,
            remaining_quantity=0,
            price=104.0,
            side='sell',
            status='FILLED',
        )
        db.add_all([active_buy, partial_buy, filled_buy, active_sell, partial_sell, filled_sell])
        db.commit()

    with TestClient(app) as client:
        with client.websocket_connect('/ws/orderbook') as websocket:
            payload = websocket.receive_json()

            bids = payload['bids']
            asks = payload['asks']
            assert bids[0]['price'] == 100.0
            assert bids[0]['quantity'] == 80
            assert bids[1]['price'] == 99.0
            assert bids[1]['quantity'] == 60
            assert all(level['price'] != 98.0 for level in bids)
            assert asks[0]['price'] == 102.0
            assert asks[0]['quantity'] == 70
            assert asks[1]['price'] == 103.0
            assert asks[1]['quantity'] == 60
            assert all(level['price'] != 104.0 for level in asks)
            assert payload['best_bid'] == 100.0
            assert payload['best_ask'] == 102.0
            assert payload['spread'] == 2.0


def test_ws_orderbook_emits_snapshot_payload():
    with SessionLocal() as db:
        buyer = User(
            company_name='Acme',
            name='Orderbook Buyer',
            email='orderbook-buyer@example.com',
            password='secret',
            role='BUYER',
        )
        seller = User(
            company_name='Acme',
            name='Orderbook Seller',
            email='orderbook-seller@example.com',
            password='secret',
            role='SELLER',
        )
        db.add_all([buyer, seller])
        db.commit()
        db.refresh(buyer)
        db.refresh(seller)

        product = Product(
            seller_id=seller.id,
            metal='Copper',
            grade='CATH',
            quantity=50,
            unit='TON',
            price=101.0,
            status='available',
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        order = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=10,
            price=100.0,
            status='PENDING',
        )
        db.add(order)
        db.commit()

    with TestClient(app) as client:
        with client.websocket_connect('/ws/orderbook') as websocket:
            payload = websocket.receive_json()

            assert 'bids' in payload
            assert 'asks' in payload
            assert 'best_bid' in payload
            assert 'best_ask' in payload
            assert 'spread' in payload
            assert 'time' in payload

            assert isinstance(payload['bids'], list)
            assert isinstance(payload['asks'], list)
            assert isinstance(payload['best_bid'], (int, float))
            assert isinstance(payload['best_ask'], (int, float))
            assert isinstance(payload['spread'], (int, float))
            assert isinstance(payload['time'], str)
            assert payload['time']
            assert payload['bids'][0]['price'] == 100.0
            assert payload['asks'][0]['price'] == 101.0
            assert payload['best_bid'] == payload['bids'][0]['price']
            assert payload['best_ask'] == payload['asks'][0]['price']
            assert payload['spread'] == payload['best_ask'] - payload['best_bid']

            assert isinstance(payload['bids'][0]['quantity'], (int, float))
            assert isinstance(payload['asks'][0]['quantity'], (int, float))
