from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect


pytestmark = pytest.mark.browser


def api_fetch(page, backend_url, path, method='GET', body=None):
    return page.evaluate(
        '''async ({ backendUrl, path, method, body }) => {
            const token = window.sessionStorage.getItem('nme_auth_token');
            const headers = {};

            if (body !== null) {
                headers['Content-Type'] = 'application/json';
            }

            if (token) {
                headers.Authorization = `Bearer ${token}`;
            }

            const init = { method, headers };
            if (body !== null) {
                init.body = JSON.stringify(body);
            }

            const response = await fetch(backendUrl + path, init);
            const text = await response.text();
            let data = null;

            if (text) {
                try {
                    data = JSON.parse(text);
                } catch (error) {
                    data = text;
                }
            }

            return { status: response.status, data };
        }''',
        {
            'backendUrl': backend_url,
            'path': path,
            'method': method,
            'body': body,
        },
    )


def login_user(page, frontend_url, backend_url, email, password='secret'):
    page.goto(frontend_url, wait_until='domcontentloaded')
    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()

    if page.locator('input[type="email"]').count() == 0:
        page.get_by_role('button', name='로그인 화면').click()

    expect(page.locator('input[type="email"]')).to_be_visible()

    page.locator('input[type="email"]').fill(email)
    page.locator('input[type="password"]').fill(password)
    page.get_by_role('button', name='로그인').click()

    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()

    auth_me = api_fetch(page, backend_url, '/auth/me')
    assert auth_me['status'] == 200
    assert auth_me['data']['email'] == email

    auth_sessions = api_fetch(page, backend_url, '/auth/sessions')
    assert auth_sessions['status'] == 200
    assert isinstance(auth_sessions['data'], list)
    assert any(session['is_current'] for session in auth_sessions['data'])

    user_info = api_fetch(page, backend_url, f"/users/{auth_me['data']['id']}")
    assert user_info['status'] == 200

    return auth_me['data']


def accept_dialogs(page):
    page.on('dialog', lambda dialog: dialog.accept())


def save_screenshot(page, screenshot_dir: Path, name: str):
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_dir / name), full_page=True)


def test_browser_trade_lifecycle(browser, browser_frontend_url, browser_backend_url, seeded_ids, tmp_path):
    console_errors = []
    page_errors = []
    request_failures = []
    api_error_responses = []
    browser_error_responses = []
    screenshot_dir = tmp_path / 'screenshots'

    buyer_context = browser.new_context()
    seller_context = browser.new_context()
    buyer_page = buyer_context.new_page()
    seller_page = seller_context.new_page()

    def attach_watchers(page):
        def on_console(message):
            if message.type == 'error':
                console_errors.append(message.text)

        def on_pageerror(error):
            page_errors.append(str(error))

        def on_requestfailed(request):
            if request.url.startswith(browser_backend_url):
                request_failures.append(f'{request.method} {request.url} -> {request.failure}')

        def on_response(response):
            if response.status >= 400:
                browser_error_responses.append(f'{response.status} {response.request.method} {response.url}')
            if response.url.startswith(browser_backend_url) and response.status >= 400:
                api_error_responses.append(f'{response.status} {response.request.method} {response.url}')

        page.on('console', on_console)
        page.on('pageerror', on_pageerror)
        page.on('requestfailed', on_requestfailed)
        page.on('response', on_response)
        accept_dialogs(page)

    attach_watchers(buyer_page)
    attach_watchers(seller_page)

    buyer_user = login_user(buyer_page, browser_frontend_url, browser_backend_url, 'bob@example.com')
    assert buyer_user['role'] == 'BUYER'

    buyer_page.get_by_role('button', name='Market').click()
    expect(buyer_page.get_by_role('heading', name='NME Live Market')).to_be_visible()

    first_product = buyer_page.locator('.grid .card').first
    expect(first_product).to_be_visible()
    first_product.get_by_role('button', name='거래 제안').click()

    quantity = 2
    proposed_price = seeded_ids['product_price'] + 111
    deal_form_numbers = buyer_page.locator('.deal-form input[type="number"]')
    expect(deal_form_numbers).to_have_count(2)
    deal_form_numbers.nth(0).fill(str(quantity))
    deal_form_numbers.nth(1).fill(str(proposed_price))
    buyer_page.get_by_role('button', name='거래 제안 보내기').click()

    expect(buyer_page.get_by_role('heading', name='Deal Room')).to_be_visible()
    deal_room_text = buyer_page.locator('.deal-room .deal-row').text_content()
    assert deal_room_text is not None
    deal_id_match = re.search(r'Deal\s+#?(\d+)', deal_room_text)
    assert deal_id_match is not None
    deal_id = int(deal_id_match.group(1))
    save_screenshot(buyer_page, screenshot_dir, 'buyer-market.png')

    seller_user = login_user(seller_page, browser_frontend_url, browser_backend_url, 'charlie@example.com')
    assert seller_user['role'] == 'SELLER'

    seller_page.get_by_role('button', name='거래 이력').click()
    expect(seller_page.get_by_role('heading', name='거래 이력')).to_be_visible()
    seller_page.get_by_role('button', name='전체 거래').click()
    expect(seller_page.get_by_text(f'Deal #{deal_id}')).to_be_visible()
    seller_page.get_by_role('button', name='상세 보기').first.click()
    expect(seller_page.get_by_role('heading', name=f'Deal #{deal_id} 상세')).to_be_visible()
    expect(seller_page.get_by_text('거래 승인 대기')).to_be_visible()

    seller_approve = api_fetch(
        seller_page,
        browser_backend_url,
        f'/deals/{deal_id}/status',
        method='PATCH',
        body={'status': 'AGREED'},
    )
    assert seller_approve['status'] == 200
    assert seller_approve['data']['status'] == 'AGREED'

    seller_page.get_by_role('button', name='이력 새로고침').click()
    expect(seller_page.get_by_role('heading', name='거래 이력')).to_be_visible()
    seller_page.get_by_role('button', name='전체 거래').click()
    expect(seller_page.get_by_text('주문 생성 가능')).to_be_visible()
    save_screenshot(seller_page, screenshot_dir, 'seller-deal.png')

    buyer_page.get_by_role('button', name='거래 관리').click()
    expect(buyer_page.get_by_role('heading', name='Deal Room')).to_be_visible()

    buyer_refresh = api_fetch(buyer_page, browser_backend_url, f'/deals/{deal_id}')
    assert buyer_refresh['status'] == 200
    assert buyer_refresh['data']['status'] == 'AGREED'

    buyer_page.get_by_role('button', name='상태 새로고침').click()
    expect(buyer_page.get_by_role('button', name='주문 생성')).to_be_visible()
    buyer_page.get_by_role('button', name='주문 생성').click()
    expect(buyer_page.get_by_role('heading', name=re.compile(r'Order #\d+'))).to_be_visible()

    order_room_text = buyer_page.locator('.order-room h4').text_content()
    assert order_room_text is not None
    order_id_match = re.search(r'Order\s+#?(\d+)', order_room_text)
    assert order_id_match is not None
    order_id = int(order_id_match.group(1))

    buyer_order = api_fetch(buyer_page, browser_backend_url, f'/deals/{deal_id}/order')
    assert buyer_order['status'] == 200
    assert buyer_order['data']['id'] == order_id
    assert buyer_order['data']['product_id'] == seeded_ids['product_id']
    assert buyer_order['data']['buyer_id'] == buyer_user['id']

    for next_status in ['ACCEPTED', 'PAID', 'SHIPPED', 'COMPLETED']:
        button_label = {
            'ACCEPTED': '주문 승인',
            'PAID': '결제 완료',
            'SHIPPED': '출하 처리',
            'COMPLETED': '거래 완료',
        }[next_status]
        buyer_page.get_by_role('button', name=button_label).click()
        expect(buyer_page.locator('.order-room .status-badge')).to_have_text(next_status)

    completion = api_fetch(buyer_page, browser_backend_url, f'/deals/{deal_id}/completion')
    assert completion['status'] == 200
    assert completion['data']['deal_id'] == deal_id
    assert completion['data']['order_id'] == order_id
    assert completion['data']['completed'] is True

    allowed_404_patterns = [f'/deals/{deal_id}/order']
    unexpected_browser_errors = [
        response
        for response in browser_error_responses
        if not any(pattern in response for pattern in allowed_404_patterns)
    ]
    unexpected_api_errors = [
        response
        for response in api_error_responses
        if not any(pattern in response for pattern in allowed_404_patterns)
    ]
    filtered_console_errors = [] if not unexpected_browser_errors else console_errors

    buyer_page.get_by_role('button', name='거래 이력').click()
    expect(buyer_page.get_by_role('heading', name='거래 이력')).to_be_visible()
    buyer_page.get_by_role('button', name='이력 새로고침').click()
    history_card = buyer_page.locator('.history-card').filter(has_text=f'Deal #{deal_id}')
    expect(history_card).to_be_visible()
    expect(history_card).to_contain_text('Order ID:')
    expect(history_card).to_contain_text('거래 완료')
    save_screenshot(buyer_page, screenshot_dir, 'history.png')

    history_card.get_by_role('button', name='상세 보기').click()
    expect(buyer_page.get_by_role('heading', name=f'Deal #{deal_id} 상세')).to_be_visible()
    expect(buyer_page.get_by_text('완료 여부:')).to_be_visible()
    expect(buyer_page.get_by_text('YES')).to_be_visible()
    save_screenshot(buyer_page, screenshot_dir, 'order-completed.png')

    buyer_page.get_by_role('button', name='거래 이력').click()
    dashboard_cards = buyer_page.locator('.dashboard-grid .dashboard-card')
    expect(dashboard_cards).to_have_count(5)
    expect(dashboard_cards.nth(0)).to_contain_text('1건')
    expect(dashboard_cards.nth(1)).to_contain_text('0건')
    expect(dashboard_cards.nth(2)).to_contain_text('1건')
    expect(dashboard_cards.nth(3)).to_contain_text('0건')
    expect(dashboard_cards.nth(4)).to_contain_text('0건')
    save_screenshot(buyer_page, screenshot_dir, 'dashboard.png')

    seller_page.get_by_role('button', name='거래 이력').click()
    seller_page.get_by_role('button', name='이력 새로고침').click()
    expect(seller_page.get_by_text(f'Deal #{deal_id}')).to_be_visible()
    expect(seller_page.get_by_role('heading', name='주문 정보')).to_be_visible()
    expect(seller_page.get_by_text('Order ID:')).to_be_visible()
    expect(seller_page.get_by_text('완료 여부:')).to_be_visible()
    expect(seller_page.get_by_text('YES')).to_be_visible()

    assert page_errors == []
    assert unexpected_browser_errors == [], f'unexpected browser error responses: {unexpected_browser_errors}'
    assert unexpected_api_errors == [], f'unexpected API error responses: {unexpected_api_errors}'
    assert filtered_console_errors == [], f'console errors: {console_errors}; browser error responses: {browser_error_responses}'
    assert request_failures == []
