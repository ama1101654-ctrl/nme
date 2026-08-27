import pytest


pytestmark = pytest.mark.security


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['access_token']
    assert payload['refresh_token']
    return payload


def test_login_me_sessions_refresh_logout_rotation(client):
    buyer = login(client, 'bob@example.com')

    buyer_me = client.get('/auth/me', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_me.status_code == 200
    assert buyer_me.json()['role'] == 'BUYER'

    buyer_sessions = client.get('/auth/sessions', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_sessions.status_code == 200
    buyer_sessions_data = buyer_sessions.json()
    assert isinstance(buyer_sessions_data, list)
    assert any(session['is_current'] for session in buyer_sessions_data)

    rotated = client.post('/auth/refresh', json={'refresh_token': buyer['refresh_token']})
    assert rotated.status_code == 200
    rotated_payload = rotated.json()
    assert rotated_payload['access_token']
    assert rotated_payload['refresh_token']

    old_refresh_reuse = client.post('/auth/refresh', json={'refresh_token': buyer['refresh_token']})
    assert old_refresh_reuse.status_code == 401

    logout_response = client.post(
        '/auth/logout',
        headers={'Authorization': f"Bearer {rotated_payload['access_token']}"},
        json={'refresh_token': rotated_payload['refresh_token']},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()['status'] == 'logged_out'

    logout_refresh_reuse = client.post('/auth/refresh', json={'refresh_token': rotated_payload['refresh_token']})
    assert logout_refresh_reuse.status_code == 401


def test_seller_session_ownership_and_revoke_all(client):
    buyer = login(client, 'bob@example.com')
    buyer_sessions = client.get('/auth/sessions', headers={'Authorization': f"Bearer {buyer['access_token']}"})
    assert buyer_sessions.status_code == 200
    buyer_session_id = buyer_sessions.json()[0]['id']

    seller = login(client, 'charlie@example.com')
    seller_me = client.get('/auth/me', headers={'Authorization': f"Bearer {seller['access_token']}"})
    assert seller_me.status_code == 200
    assert seller_me.json()['role'] == 'SELLER'

    revoke_attempt = client.post(
        f'/auth/sessions/{buyer_session_id}/revoke',
        headers={'Authorization': f"Bearer {seller['access_token']}"},
    )
    assert revoke_attempt.status_code == 404

    revoke_all = client.post(
        '/auth/sessions/revoke-all',
        headers={'Authorization': f"Bearer {buyer['access_token']}"},
    )
    assert revoke_all.status_code == 200
    assert revoke_all.json()['status'] == 'all_sessions_revoked'


def test_cors_regression(client):
    allowed_localhost = client.get('/market', headers={'Origin': 'http://localhost:5174'})
    allowed_loopback = client.get('/market', headers={'Origin': 'http://127.0.0.1:5174'})
    denied_evil = client.get('/market', headers={'Origin': 'http://evil.example.com'})
    assert allowed_localhost.status_code == 200
    assert allowed_localhost.headers.get('access-control-allow-origin') == 'http://localhost:5174'
    assert allowed_loopback.status_code == 200
    assert allowed_loopback.headers.get('access-control-allow-origin') == 'http://127.0.0.1:5174'
    assert denied_evil.status_code == 200
    assert denied_evil.headers.get('access-control-allow-origin') is None


def test_rate_limit_regression(client):
    for _ in range(10):
        response = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
        assert response.status_code == 200

    rate_limit_response = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
    assert rate_limit_response.status_code == 429

    # Use a fresh client fixture in a new test invocation for refresh regression.
    # The login bucket is intentionally isolated per test case by conftest.


def test_refresh_rate_limit_regression(client):
    buyer = login(client, 'bob@example.com')
    refresh_token = buyer['refresh_token']
    for _ in range(30):
        response = client.post('/auth/refresh', json={'refresh_token': refresh_token})
        assert response.status_code == 200
        payload = response.json()
        assert payload['access_token']
        assert payload['refresh_token']
        refresh_token = payload['refresh_token']

    refresh_rate_limit_response = client.post('/auth/refresh', json={'refresh_token': refresh_token})
    assert refresh_rate_limit_response.status_code == 429
