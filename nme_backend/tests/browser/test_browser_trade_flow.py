from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

from app.database import SessionLocal
from app.main import create_access_token
from app.models import Company, CompanyMember, Contract, ContractRevision, InvestorProfile, MemberProfile, Order, Trade, User


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


def open_authenticated_session(page, frontend_url, user_id):
    page.goto(frontend_url, wait_until='domcontentloaded')
    page.evaluate(
        '''({ token, userId }) => {
            window.sessionStorage.setItem('nme_auth_token', token);
            window.sessionStorage.setItem('nme_auth_user_id', String(userId));
        }''',
        {'token': create_access_token(user_id), 'userId': user_id},
    )
    page.reload(wait_until='domcontentloaded')
    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()


def accept_dialogs(page):
    page.on('dialog', lambda dialog: dialog.accept())


def save_screenshot(page, screenshot_dir: Path, name: str):
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(screenshot_dir / name), full_page=True)


def install_websocket_probe(page):
    page.add_init_script(
        '''(() => {
            const NativeWebSocket = window.WebSocket;
            const paths = ['/ws/ticker', '/ws/orderbook', '/ws/trades'];
            const metrics = {
                created: Object.fromEntries(paths.map(path => [path, 0])),
                active: Object.fromEntries(paths.map(path => [path, 0])),
                messages: Object.fromEntries(paths.map(path => [path, 0])),
                closes: Object.fromEntries(paths.map(path => [path, 0])),
            };
            const sockets = [];

            class TrackedWebSocket extends NativeWebSocket {
                constructor(url, protocols) {
                    if (protocols === undefined) {
                        super(url);
                    } else {
                        super(url, protocols);
                    }

                    const path = new URL(String(url), window.location.href).pathname;
                    sockets.push({ path, socket: this });
                    metrics.created[path] = (metrics.created[path] || 0) + 1;
                    this.addEventListener('open', () => {
                        metrics.active[path] = (metrics.active[path] || 0) + 1;
                    });
                    this.addEventListener('message', () => {
                        metrics.messages[path] = (metrics.messages[path] || 0) + 1;
                    });
                    this.addEventListener('close', () => {
                        metrics.active[path] = Math.max(0, (metrics.active[path] || 0) - 1);
                        metrics.closes[path] = (metrics.closes[path] || 0) + 1;
                    });
                }
            }

            window.WebSocket = TrackedWebSocket;
            window.__nmeWebSocketProbe = {
                snapshot: () => {
                    const open = Object.fromEntries(paths.map(path => [path, 0]));
                    for (const entry of sockets) {
                        if (entry.socket.readyState === NativeWebSocket.OPEN) {
                            open[entry.path] = (open[entry.path] || 0) + 1;
                        }
                    }
                    return JSON.parse(JSON.stringify({ ...metrics, open }));
                },
                closeAll: () => {
                    let closed = 0;
                    for (const entry of sockets) {
                        if (paths.includes(entry.path) && entry.socket.readyState === NativeWebSocket.OPEN) {
                            entry.socket.close(4000, 'NME browser reconnect test');
                            closed += 1;
                        }
                    }
                    return closed;
                },
                inject: (path, data) => {
                    const entry = [...sockets].reverse().find(
                        item => item.path === path && item.socket.readyState === NativeWebSocket.OPEN
                    );
                    if (!entry) return false;
                    entry.socket.dispatchEvent(new MessageEvent('message', { data }));
                    return true;
                },
            };
        })()'''
    )


def test_browser_member_identity_context(browser, browser_frontend_url, browser_backend_url):
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == 'bob@example.com').one()
        seller = db.query(User).filter(User.email == 'charlie@example.com').one()
        admin = db.query(User).filter(User.email == 'alice@example.com').one()
        company = Company(
            company_name='ABC Metals',
            business_registration_number='BRN-BROWSER-001',
            country='KR',
        )
        db.add_all([
            company,
            MemberProfile(user_id=buyer.id, member_type='COMPANY', display_name='ABC Metals Buyer'),
            MemberProfile(user_id=seller.id, member_type='SEARCH', display_name='Market Searcher'),
            MemberProfile(user_id=admin.id, member_type='INVESTOR', display_name='NME Investor'),
            InvestorProfile(user_id=admin.id, investor_type='CORPORATE', display_name='NME Investor', country='KR'),
        ])
        db.flush()
        db.add(CompanyMember(company_id=company.id, user_id=buyer.id, trading_role='BUYER'))
        db.commit()

    contexts = []
    try:
        for email, expected_identity in [
            ('bob@example.com', 'NME Member: COMPANY · ABC Metals · BUYER'),
            ('charlie@example.com', 'NME Member: SEARCH'),
            ('alice@example.com', 'NME Member: INVESTOR · CORPORATE'),
        ]:
            context = browser.new_context()
            contexts.append(context)
            page = context.new_page()
            login_user(page, browser_frontend_url, browser_backend_url, email)
            expect(page.locator('.member-context')).to_have_text(expected_identity)
            expect(page.get_by_role('button', name='Market')).to_be_visible()
    finally:
        for context in contexts:
            context.close()


def test_browser_password_security_login_and_logout(page, browser_frontend_url, browser_backend_url):
    page.goto(browser_frontend_url, wait_until='domcontentloaded')
    password_input = page.locator('input[type="password"]')
    expect(password_input).to_be_visible()

    page.locator('input[type="email"]').fill('bob@example.com')
    password_input.fill('wrong-password')
    page.get_by_role('button', name='로그인').click()
    expect(page.get_by_text('이메일 또는 비밀번호를 확인해 주세요.')).to_be_visible()
    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()

    password_input.fill('secret')
    page.get_by_role('button', name='로그인').click()
    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()
    expect(page.locator('.member-context')).to_be_visible()
    expect(page.get_by_role('button', name='BUY 주문').first).to_be_visible()
    expect(page.get_by_role('button', name='SELL 주문').first).to_be_visible()

    stored_values = page.evaluate(
        """() => ({
            local: Object.values(localStorage),
            session: Object.values(sessionStorage),
        })"""
    )
    assert 'secret' not in stored_values['local']
    assert 'secret' not in stored_values['session']
    assert 'wrong-password' not in stored_values['local']
    assert 'wrong-password' not in stored_values['session']
    assert 'secret' not in page.locator('body').inner_text()

    page.get_by_role('button', name='로그아웃').click()
    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()
    assert api_fetch(page, browser_backend_url, '/members/me')['status'] == 401


def test_browser_contract_detail_from_trade_history(page, browser_frontend_url, browser_backend_url, seeded_ids):
    with SessionLocal() as db:
        buy_order = Order(
            product_id=seeded_ids['product_id'],
            buyer_id=seeded_ids['buyer_id'],
            quantity=10,
            remaining_quantity=0,
            price=2400,
            side='buy',
            status='FILLED',
        )
        sell_order = Order(
            product_id=seeded_ids['product_id'],
            seller_id=seeded_ids['seller_id'],
            quantity=10,
            remaining_quantity=0,
            price=2400,
            side='sell',
            status='FILLED',
        )
        db.add_all([buy_order, sell_order])
        db.flush()
        trade = Trade(
            product_id=seeded_ids['product_id'],
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            quantity=10,
            price=2400,
        )
        db.add(trade)
        db.flush()
        contract = Contract(
            contract_no=f'NME-CT-2026-{trade.id:010d}',
            trade_id=trade.id,
            product_id=seeded_ids['product_id'],
            buyer_id=seeded_ids['buyer_id'],
            seller_id=seeded_ids['seller_id'],
            quantity=10,
            unit='TON',
            price=2400,
            currency='KRW',
            total_value=24000,
            status='DRAFT',
            brand='PMB',
            tolerance=None,
            quotation_period='Unknown On Day',
            delivery_term='CIF',
            delivery_location='Incheon',
            payment_term='T/T Korean Dollar',
            partial_delivery='YES',
        )
        db.add(contract)
        db.flush()
        db.add(ContractRevision(
            contract_id=contract.id,
            revision_no=1,
            revision_status='DRAFT',
            contract_no=contract.contract_no,
            trade_id=contract.trade_id,
            product_id=contract.product_id,
            buyer_id=contract.buyer_id,
            seller_id=contract.seller_id,
            quantity=contract.quantity,
            unit=contract.unit,
            price=contract.price,
            currency=contract.currency,
            total_value=contract.total_value,
            status=contract.status,
            brand=contract.brand,
            tolerance=contract.tolerance,
            quotation_period=contract.quotation_period,
            delivery_term=contract.delivery_term,
            delivery_location=contract.delivery_location,
            payment_term=contract.payment_term,
            partial_delivery=contract.partial_delivery,
        ))
        missing_buy_order = Order(
            product_id=seeded_ids['product_id'],
            buyer_id=seeded_ids['buyer_id'],
            quantity=5,
            remaining_quantity=0,
            price=2300,
            side='buy',
            status='FILLED',
        )
        missing_sell_order = Order(
            product_id=seeded_ids['product_id'],
            seller_id=seeded_ids['seller_id'],
            quantity=5,
            remaining_quantity=0,
            price=2300,
            side='sell',
            status='FILLED',
        )
        db.add_all([missing_buy_order, missing_sell_order])
        db.flush()
        missing_contract_trade = Trade(
            product_id=seeded_ids['product_id'],
            buy_order_id=missing_buy_order.id,
            sell_order_id=missing_sell_order.id,
            quantity=5,
            price=2300,
        )
        db.add(missing_contract_trade)
        db.commit()
        trade_id = trade.id
        missing_contract_trade_id = missing_contract_trade.id
        contract_no = contract.contract_no

    open_authenticated_session(page, browser_frontend_url, seeded_ids['buyer_id'])
    page.get_by_role('button', name='거래 이력').click()
    page.get_by_role('button', name='보기').first.click()

    expect(page.get_by_role('heading', name=f'Trade #{missing_contract_trade_id} 상세')).to_be_visible()
    expect(page.get_by_text('No contract available')).to_be_visible()
    expect(page.locator('.contract-detail .error-msg')).to_have_count(0)

    page.get_by_role('button', name='보기').nth(1).click()
    expect(page.get_by_role('heading', name=f'Trade #{trade_id} 상세')).to_be_visible()
    expect(page.get_by_role('heading', name='Contract Detail')).to_be_visible()
    expect(page.get_by_role('heading', name='Contract Basic Information')).to_be_visible()
    expect(page.get_by_role('heading', name='Trade Information')).to_be_visible()
    expect(page.get_by_role('heading', name='Contract Terms')).to_be_visible()
    expect(page.locator('.contract-detail')).to_contain_text(contract_no)
    expect(page.locator('.contract-detail')).to_contain_text('PMB')
    expect(page.locator('.contract-detail')).to_contain_text('Unknown On Day')
    expect(page.locator('.contract-detail')).to_contain_text('T/T Korean Dollar')
    expect(page.locator('.contract-grid > div', has_text='Tolerance').locator('dd')).to_have_text('-')
    expect(page.get_by_role('heading', name='Revision History')).to_be_visible()
    expect(page.locator('.revision-table')).to_contain_text('DRAFT')
    page.locator('.revision-table').get_by_role('button', name='보기').click()
    expect(page.get_by_role('heading', name='Revision #1 Detail')).to_be_visible()
    expect(page.locator('.revision-detail')).to_contain_text('PMB')
    expect(page.locator('.revision-detail')).to_contain_text('T/T Korean Dollar')
    expect(page.get_by_role('button', name=re.compile('Edit|Delete|Approve|Reject|Apply Revision|Modify Terms'))).to_have_count(0)


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

    buyer_page.get_by_role('button', name='로그아웃').click()
    expect(buyer_page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()

    assert page_errors == []
    assert unexpected_browser_errors == [], f'unexpected browser error responses: {unexpected_browser_errors}'
    assert unexpected_api_errors == [], f'unexpected API error responses: {unexpected_api_errors}'
    assert filtered_console_errors == [], f'console errors: {console_errors}; browser error responses: {browser_error_responses}'
    assert request_failures == []


def test_browser_websocket_disconnect_reconnect_and_cleanup(browser, browser_frontend_url, browser_backend_url):
    paths = ['/ws/ticker', '/ws/orderbook', '/ws/trades']
    context = browser.new_context()
    page = context.new_page()
    page_errors = []
    page.on('pageerror', lambda error: page_errors.append(str(error)))
    install_websocket_probe(page)

    login_user(page, browser_frontend_url, browser_backend_url, 'bob@example.com')
    ticker_status = page.locator('.signal-pill')
    orderbook_status = page.locator('.orderbook-panel .feed-status-row')
    trade_status = page.locator('.trade-panel .feed-status-row')
    expect(ticker_status).to_contain_text('LIVE')
    expect(orderbook_status).to_contain_text('LIVE')
    expect(trade_status).to_contain_text('LIVE')

    page.wait_for_function(
        '''paths => {
            const snapshot = window.__nmeWebSocketProbe.snapshot();
            return paths.every(path => snapshot.open[path] >= 1 && snapshot.messages[path] > 0);
        }''',
        arg=paths,
    )
    before_disconnect = page.evaluate('() => window.__nmeWebSocketProbe.snapshot()')
    assert all(before_disconnect['open'][path] == 1 for path in paths), before_disconnect
    ticker_time_before = page.locator('.ticker-card.primary .ticker-timestamp').inner_text()
    orderbook_time_before = page.locator('.orderbook-panel .orderbook-time').inner_text()
    trade_row_before = page.locator('.trade-panel .trade-table tbody tr').first.inner_text()

    page.get_by_role('button', name='거래 이력').click()
    expect(page.get_by_role('heading', name='거래 이력')).to_be_visible()
    page.get_by_role('button', name='Market').click()
    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()
    after_navigation = page.evaluate('() => window.__nmeWebSocketProbe.snapshot()')
    assert all(after_navigation['open'][path] == 1 for path in paths)
    assert after_navigation['created'] == before_disconnect['created']

    page.evaluate(
        '''() => {
            const selectors = {
                ticker: '.signal-pill',
                orderbook: '.orderbook-panel .feed-status-row',
                trades: '.trade-panel .feed-status-row',
            };
            window.__nmeStatusTransitions = Object.fromEntries(
                Object.entries(selectors).map(([name, selector]) => {
                    const element = document.querySelector(selector);
                    const values = [element?.textContent?.trim() || ''];
                    new MutationObserver(() => values.push(element?.textContent?.trim() || ''))
                        .observe(element, { childList: true, subtree: true, characterData: true });
                    return [name, values];
                })
            );
        }'''
    )
    closed_count = page.evaluate('() => window.__nmeWebSocketProbe.closeAll()')
    assert closed_count == 3
    expect(ticker_status).to_contain_text('DISCONNECTED')
    expect(orderbook_status).to_contain_text('DISCONNECTED')
    expect(trade_status).to_contain_text('DISCONNECTED')

    page.wait_for_function(
        '''({ paths, before }) => {
            const snapshot = window.__nmeWebSocketProbe.snapshot();
            return paths.every(path =>
                snapshot.created[path] === before.created[path] + 1 &&
                snapshot.open[path] === 1 &&
                snapshot.messages[path] > before.messages[path]
            );
        }''',
        arg={'paths': paths, 'before': before_disconnect},
        timeout=10000,
    )
    expect(ticker_status).to_contain_text('LIVE')
    expect(orderbook_status).to_contain_text('LIVE')
    expect(trade_status).to_contain_text('LIVE')
    expect(page.locator('.ticker-card.primary .ticker-timestamp')).not_to_have_text(ticker_time_before)
    expect(page.locator('.orderbook-panel .orderbook-time')).not_to_have_text(orderbook_time_before)
    expect(page.locator('.trade-panel .trade-table tbody tr').first).not_to_have_text(trade_row_before)
    trade_ids = page.locator('.trade-panel tr[data-trade-id]').evaluate_all(
        '(rows) => rows.map(row => row.dataset.tradeId)'
    )
    assert len(trade_ids) == len(set(trade_ids))
    status_transitions = page.evaluate('() => window.__nmeStatusTransitions')
    assert any('DISCONNECTED' in value for value in status_transitions['ticker'])
    assert any('RECONNECTING' in value for value in status_transitions['ticker'])
    assert any('DISCONNECTED' in value for value in status_transitions['orderbook'])
    assert any('RECONNECTING' in value for value in status_transitions['orderbook'])
    assert any('DISCONNECTED' in value for value in status_transitions['trades'])
    assert any('RECONNECTING' in value for value in status_transitions['trades'])

    orderbook_before_malformed = page.locator('.orderbook-shell').inner_text()
    trade_before_malformed = page.locator('.trade-panel .trade-table tbody').inner_text()
    malformed_payloads = [
        'not-json',
        '{}',
        'null',
        '{"price":"abc","time":"invalid"}',
        '{"bids":[],"asks":[],"best_bid":"abc","best_ask":null,"spread":null,"time":"invalid"}',
        '{"trade_id":1,"product_id":1,"price":"abc","quantity":"abc","side":"hold","time":"invalid"}',
    ]
    for malformed_payload in malformed_payloads:
        assert page.evaluate(
            '''payload => {
            const probe = window.__nmeWebSocketProbe;
            return probe.inject('/ws/ticker', payload) &&
                probe.inject('/ws/orderbook', payload) &&
                probe.inject('/ws/trades', payload);
        }''',
            malformed_payload,
        ) is True
    page.wait_for_timeout(100)
    assert 'NaN' not in page.locator('.ticker-card.primary').inner_text()
    assert 'Invalid Date' not in page.locator('.ticker-card.primary').inner_text()
    assert page.locator('.orderbook-shell').inner_text() == orderbook_before_malformed
    assert page.locator('.trade-panel .trade-table tbody').inner_text() == trade_before_malformed
    assert page_errors == []

    page.reload(wait_until='domcontentloaded')
    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()
    page.wait_for_function(
        '''paths => {
            const snapshot = window.__nmeWebSocketProbe.snapshot();
            return paths.every(path => snapshot.open[path] === 1 && snapshot.messages[path] > 0);
        }''',
        arg=paths,
    )

    page.get_by_role('button', name='로그아웃').click()
    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()
    page.wait_for_function(
        '''paths => {
            const snapshot = window.__nmeWebSocketProbe.snapshot();
            return paths.every(path => snapshot.open[path] === 0);
        }''',
        arg=paths,
    )
    after_logout = page.evaluate('() => window.__nmeWebSocketProbe.snapshot()')
    page.wait_for_timeout(1500)
    assert page.evaluate('() => window.__nmeWebSocketProbe.snapshot()')['created'] == after_logout['created']


def test_browser_direct_buy_sell_match(browser, browser_frontend_url, browser_backend_url, seeded_ids):
    buyer_context = browser.new_context()
    seller_context = browser.new_context()
    buyer_page = buyer_context.new_page()
    seller_page = seller_context.new_page()
    accept_dialogs(buyer_page)
    accept_dialogs(seller_page)

    seller_user = login_user(seller_page, browser_frontend_url, browser_backend_url, 'charlie@example.com')
    assert seller_user['role'] == 'SELLER'
    seller_card = seller_page.locator('.grid .card').first
    seller_card.get_by_role('button', name='SELL 주문').click()
    expect(seller_page.get_by_role('heading', name='SELL 직접 주문')).to_be_visible()
    expect(seller_page.get_by_text('주문 수량 (TON)')).to_be_visible()
    expect(seller_page.get_by_text('주문 가격 (KRW / TON)')).to_be_visible()
    expect(seller_page.get_by_text('SELL 주문 수량은 체결 전까지 판매 재고에서 예약됩니다.')).to_be_visible()
    seller_page.get_by_label('직접 주문 수량').fill('40')
    seller_page.get_by_label('직접 주문 가격').fill('2500')
    seller_page.get_by_role('button', name='SELL 주문 생성').click()
    expect(seller_page.get_by_text('SELL 주문과 재고 예약이 생성되었습니다.')).to_be_visible()
    seller_order = seller_page.locator('.proposal .order-room')
    expect(seller_order).to_contain_text('Side: SELL')
    expect(seller_order).to_contain_text('Quantity (주문): 40 TON')
    expect(seller_order).to_contain_text('Filled (체결): 0 TON')
    expect(seller_order).to_contain_text('Remaining (미체결): 40 TON')
    expect(seller_order).to_contain_text('₩2,500 / TON')
    expect(seller_order).to_contain_text('주문 대기')
    seller_order_heading = seller_order.get_by_role('heading', name=re.compile(r'Order #\d+')).inner_text()
    seller_order_id = int(re.search(r'\d+', seller_order_heading).group())

    seller_page.get_by_label('직접 주문 수량').fill('101')
    seller_page.get_by_role('button', name='SELL 주문 생성').click()
    expect(seller_page.get_by_text('판매 가능 수량을 초과했습니다.')).to_be_visible()

    buyer_user = login_user(buyer_page, browser_frontend_url, browser_backend_url, 'bob@example.com')
    assert buyer_user['role'] == 'BUYER'
    buyer_card = buyer_page.locator('.grid .card').first
    buyer_card.get_by_role('button', name='SELL 주문').click()
    buyer_page.get_by_label('직접 주문 수량').fill('1')
    buyer_page.get_by_role('button', name='SELL 주문 생성').click()
    expect(buyer_page.get_by_text('Product is not owned by the authenticated seller')).to_be_visible()

    buyer_card.get_by_role('button', name='BUY 주문').click()
    buyer_page.get_by_role('button', name='BUY 주문 생성').click()
    expect(buyer_page.get_by_text('수량과 가격은 0보다 커야 합니다.')).to_be_visible()
    buyer_page.get_by_label('직접 주문 수량').fill('100')
    buyer_page.get_by_label('직접 주문 가격').fill('2500')
    buyer_page.get_by_role('button', name='BUY 주문 생성').click()
    expect(buyer_page.get_by_text('BUY 주문이 생성되었습니다.')).to_be_visible()

    buyer_order = buyer_page.locator('.proposal .order-room')
    expect(buyer_order).to_contain_text('Side: BUY')
    expect(buyer_order).to_contain_text('Quantity (주문): 100 TON')
    expect(buyer_order).to_contain_text('Remaining (미체결): 100 TON')
    buyer_order_heading = buyer_order.get_by_role('heading', name=re.compile(r'Order #\d+')).inner_text()
    buyer_order_id = int(re.search(r'\d+', buyer_order_heading).group())
    buyer_order.get_by_role('button', name='Match').click()
    expect(buyer_page.get_by_text('40 수량이 체결되었습니다.')).to_be_visible()
    expect(buyer_order).to_contain_text('Remaining (미체결): 60 TON')
    expect(buyer_order).to_contain_text('Filled (체결): 40 TON')
    expect(buyer_order).to_contain_text('부분 체결')
    expect(buyer_order).to_contain_text('일부 수량이 체결되었습니다.')

    partial_buy = api_fetch(buyer_page, browser_backend_url, f'/orders/{buyer_order_id}')
    filled_sell = api_fetch(seller_page, browser_backend_url, f'/orders/{seller_order_id}')
    assert partial_buy['data']['quantity'] == 100
    assert partial_buy['data']['remaining_quantity'] == 60
    assert partial_buy['data']['status'] == 'PARTIAL'
    assert filled_sell['data']['remaining_quantity'] == 0
    assert filled_sell['data']['status'] == 'FILLED'

    expect(buyer_page.locator('.orderbook-panel .orderbook-column').first).to_contain_text('60')
    expect(buyer_page.locator('.orderbook-panel .orderbook-column').nth(1)).not_to_contain_text('40')

    expect(buyer_page.locator('.signal-pill')).to_contain_text('LIVE')
    expect(buyer_page.locator('.orderbook-panel .feed-status-row')).to_contain_text('LIVE')
    expect(buyer_page.locator('.trade-panel .feed-status-row')).to_contain_text('LIVE')
    expect(buyer_page.locator('.trade-panel .trade-buy').first).to_contain_text('40')

    buyer_page.get_by_role('button', name='거래 이력').click()
    expect(buyer_page.get_by_role('heading', name='거래 이력')).to_be_visible()
    buyer_page.get_by_role('button', name='이력 새로고침').click()
    trade_row = buyer_page.locator('.history-section .trade-table tbody tr').first
    expect(trade_row).to_contain_text('40')
    trade_row.get_by_role('button', name='보기').click()
    trade_detail = buyer_page.locator('.history-section .detail-section')
    expect(trade_detail.get_by_role('heading', name=re.compile(r'Trade #\d+ 상세'))).to_be_visible()
    expect(trade_detail).to_contain_text(f"Product ID: #{seeded_ids['product_id']}")
    expect(trade_detail).to_contain_text('수량: 40')
    expect(trade_detail).to_contain_text('가격: ₩2,500')
    expect(trade_detail).to_contain_text('구분: BUY')

    buyer_page.get_by_role('button', name='Market').click()
    buyer_card = buyer_page.locator('.grid .card').first
    expect(buyer_card).to_contain_text('Trade Count: 1')
    expect(buyer_card).to_contain_text('Total Volume: 40 TON')
    expect(buyer_card).to_contain_text('Total Value: ₩100,000')
    expect(buyer_card).to_contain_text('Latest Price: ₩2,500 / TON')
    expect(buyer_card).to_contain_text('High / Low: ₩2,500 / ₩2,500')
    expect(buyer_card).to_contain_text('Average (VWAP): ₩2,500 / TON')

    first_summary = api_fetch(buyer_page, browser_backend_url, f"/products/{seeded_ids['product_id']}/market-summary")
    assert first_summary['status'] == 200
    assert first_summary['data']['trade_count'] == 1
    assert first_summary['data']['total_quantity'] == 40
    assert first_summary['data']['total_value'] == 100000
    assert first_summary['data']['latest_price'] == 2500
    assert first_summary['data']['high_price'] == 2500
    assert first_summary['data']['low_price'] == 2500
    assert first_summary['data']['average_price'] == 2500

    for width, height in [(1440, 900), (1280, 800), (1024, 768)]:
        buyer_page.set_viewport_size({'width': width, 'height': height})
        expect(buyer_card.get_by_role('button', name='BUY 주문')).to_be_visible()
        expect(buyer_card.get_by_role('button', name='SELL 주문')).to_be_visible()
        has_horizontal_overflow = buyer_page.evaluate(
            '() => document.documentElement.scrollWidth > document.documentElement.clientWidth'
        )
        assert has_horizontal_overflow is False, f'horizontal overflow at {width}x{height}'

    seller_page.get_by_label('직접 주문 수량').fill('60')
    seller_page.get_by_role('button', name='SELL 주문 생성').click()
    expect(seller_page.get_by_text('SELL 주문과 재고 예약이 생성되었습니다.')).to_be_visible()
    second_seller_heading = seller_page.locator('.proposal .order-room').get_by_role('heading', name=re.compile(r'Order #\d+')).inner_text()
    second_seller_order_id = int(re.search(r'\d+', second_seller_heading).group())

    buyer_order.get_by_role('button', name='Match').click()
    expect(buyer_page.get_by_text('60 수량이 체결되었습니다.')).to_be_visible()
    expect(buyer_order).to_contain_text('Remaining (미체결): 0 TON')
    expect(buyer_order).to_contain_text('Filled (체결): 100 TON')
    expect(buyer_order).to_contain_text('체결 완료')
    expect(buyer_order.get_by_role('button', name='Match')).to_be_disabled()
    expect(buyer_card).to_contain_text('Trade Count: 2')
    expect(buyer_card).to_contain_text('Total Volume: 100 TON')
    expect(buyer_card).to_contain_text('Total Value: ₩250,000')

    final_buy = api_fetch(buyer_page, browser_backend_url, f'/orders/{buyer_order_id}')
    final_sell = api_fetch(seller_page, browser_backend_url, f'/orders/{second_seller_order_id}')
    assert final_buy['data']['remaining_quantity'] == 0
    assert final_buy['data']['status'] == 'FILLED'
    assert final_sell['data']['remaining_quantity'] == 0
    assert final_sell['data']['status'] == 'FILLED'

    expect(buyer_page.locator('.orderbook-panel .orderbook-column').first).not_to_contain_text('60')
    expect(buyer_page.locator('.trade-panel .trade-buy').first).to_contain_text('60')

    final_summary = api_fetch(buyer_page, browser_backend_url, f"/products/{seeded_ids['product_id']}/market-summary")
    assert final_summary['status'] == 200
    assert final_summary['data']['trade_count'] == 2
    assert final_summary['data']['total_quantity'] == 100
    assert final_summary['data']['total_value'] == 250000
    assert final_summary['data']['latest_price'] == 2500
    assert final_summary['data']['high_price'] == 2500
    assert final_summary['data']['low_price'] == 2500
    assert final_summary['data']['average_price'] == 2500

    trade_history = api_fetch(buyer_page, browser_backend_url, '/trades')
    assert trade_history['status'] == 200
    assert sum(trade['quantity'] for trade in trade_history['data']) == 100
    assert [trade['quantity'] for trade in trade_history['data'][:2]] == [60, 40]
    assert all(trade['price'] == 2500 for trade in trade_history['data'][:2])

    buyer_page.evaluate("""() => {
        window.sessionStorage.setItem('nme_auth_token', 'expired-access-token');
        window.sessionStorage.setItem('nme_refresh_token', 'expired-refresh-token');
    }""")
    buyer_page.get_by_label('직접 주문 수량').fill('1')
    buyer_page.get_by_role('button', name='BUY 주문 생성').click()
    expect(buyer_page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()
    expect(buyer_page.get_by_text('로그인이 만료되었습니다. 다시 로그인해 주세요.')).to_be_visible()
