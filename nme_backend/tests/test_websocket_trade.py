from datetime import datetime

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Order, Product, Trade, User


def test_ws_trade_reads_from_trade_table():
    with SessionLocal() as db:
        buyer = User(company_name='Co', name='Buyer', email='trade-buyer@example.com', password='secret', role='BUYER')
        seller = User(company_name='Co', name='Seller', email='trade-seller@example.com', password='secret', role='SELLER')
        db.add_all([buyer, seller])
        db.commit(); db.refresh(buyer); db.refresh(seller)

        product = Product(seller_id=seller.id, metal='Copper', grade='CATH', quantity=100, unit='TON', price=100.0, status='available')
        db.add(product)
        db.commit(); db.refresh(product)

        buy_order = Order(product_id=product.id, buyer_id=buyer.id, quantity=100, remaining_quantity=60, price=100, side='buy', status='PARTIAL')
        sell_order = Order(product_id=product.id, seller_id=seller.id, quantity=100, remaining_quantity=0, price=99, side='sell', status='FILLED')
        db.add_all([buy_order, sell_order])
        db.commit(); db.refresh(buy_order); db.refresh(sell_order)

        product_id = product.id
        trade = Trade(product_id=product_id, buy_order_id=buy_order.id, sell_order_id=sell_order.id, quantity=40, price=99)
        db.add(trade)
        db.commit(); db.refresh(trade)

    with TestClient(app) as client:
        with client.websocket_connect('/ws/trades') as websocket:
            payload = websocket.receive_json()

            assert payload['trade_id'] == trade.id
            assert payload['product_id'] == product_id
            assert payload['price'] == 99
            assert payload['quantity'] == 40
            assert payload['side'] == 'buy'
            assert payload['time']


def _is_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def test_ws_trade_emits_trade_payload():
    with TestClient(app) as client:
        with client.websocket_connect('/ws/trades') as websocket:
            payload = websocket.receive_json()

            assert 'trade_id' in payload
            assert 'product_id' in payload
            assert 'price' in payload
            assert 'quantity' in payload
            assert 'side' in payload
            assert 'time' in payload

            assert isinstance(payload['trade_id'], int)
            assert isinstance(payload['product_id'], int)
            assert isinstance(payload['price'], (int, float))
            assert isinstance(payload['quantity'], (int, float))
            assert payload['side'] in {'buy', 'sell'}
            assert isinstance(payload['time'], str)
            assert payload['time']
            assert _is_iso8601(payload['time'])

            assert payload['price'] > 0
            assert payload['quantity'] > 0
