from fastapi.testclient import TestClient

from app.main import app


def test_ws_ticker_emits_price_and_time():
    with TestClient(app) as client:
        with client.websocket_connect('/ws/ticker') as websocket:
            payload = websocket.receive_json()
            assert 'price' in payload
            assert 'time' in payload
            assert isinstance(payload['price'], (int, float))
            assert payload['price'] > 0
            assert isinstance(payload['time'], str)
            assert payload['time']
