import pytest


pytestmark = pytest.mark.smoke


def test_api_smoke(client):
    health = client.get('/health')
    assert health.status_code == 200
    assert health.json() == {'status': 'ok'}

    market = client.get('/market')
    assert market.status_code == 200
    market_data = market.json()
    assert isinstance(market_data, list)

    docs = client.get('/docs')
    assert docs.status_code == 200
    assert 'text/html' in docs.headers.get('content-type', '').lower()

    openapi = client.get('/openapi.json')
    assert openapi.status_code == 200
    schema = openapi.json()
    paths = schema.get('paths', {})
    for path in ['/auth/login', '/auth/refresh', '/auth/me', '/auth/sessions', '/market', '/deals']:
        assert path in paths
