from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Order, Product, User


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
