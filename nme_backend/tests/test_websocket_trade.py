from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


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
