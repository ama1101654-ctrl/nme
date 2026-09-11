import pytest
from playwright.sync_api import expect

from app.database import SessionLocal
from app.models import Order, Trade


pytestmark = pytest.mark.browser


def test_browser_bootstrap_smoke(page, browser_frontend_url, browser_backend_url, seeded_ids):
    frontend_base = browser_frontend_url.rstrip('/')
    api_base = browser_backend_url.rstrip('/')

    with SessionLocal() as db:
        buy_order = Order(
            product_id=seeded_ids['product_id'],
            buyer_id=seeded_ids['buyer_id'],
            quantity=10,
            remaining_quantity=0,
            price=2500,
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
        db.commit()
        db.refresh(trade)
        trade_id = trade.id

    console_errors = []
    page_errors = []
    api_request_failures = []
    api_response_failures = []

    def on_console(message):
        if message.type == 'error':
            console_errors.append(message.text)

    def on_pageerror(error):
        page_errors.append(str(error))

    def on_requestfailed(request):
        if request.url.startswith(api_base):
            api_request_failures.append(f'{request.method} {request.url} -> {request.failure}')

    def on_response(response):
        if response.url.startswith(api_base) and response.status >= 400:
            api_response_failures.append(f'{response.status} {response.request.method} {response.url}')

    page.on('console', on_console)
    page.on('pageerror', on_pageerror)
    page.on('requestfailed', on_requestfailed)
    page.on('response', on_response)

    page.goto(frontend_base, wait_until='domcontentloaded')

    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()
    expect(page.get_by_role('button', name='개발용 기본 사용자로 계속')).to_be_visible()

    page.get_by_role('button', name='개발용 기본 사용자로 계속').click()

    expect(page.get_by_role('heading', name='NME Live Market')).to_be_visible()
    expect(page.get_by_text('현재 사용자:')).to_be_visible()
    expect(page.locator('.grid .card').first).to_be_visible()
    expect(page.locator('.signal-pill')).to_contain_text('LIVE')
    expect(page.locator('.orderbook-panel .feed-status-row')).to_contain_text('LIVE')
    expect(page.locator('.trade-panel .feed-status-row')).to_contain_text('LIVE')
    expect(page.locator('.grid .card').first).to_contain_text('Trade Count:')

    page.get_by_role('button', name='거래 이력').click()

    expect(page.get_by_role('heading', name='거래 이력')).to_be_visible()
    expect(page.get_by_role('button', name='전체 거래')).to_be_visible()
    expect(page.get_by_placeholder('Deal ID / Product ID 검색')).to_be_visible()
    expect(page.get_by_text('체결된 거래가 없습니다.')).not_to_be_visible()
    page.get_by_role('button', name='보기').first.click()
    expect(page.get_by_role('heading', name=f'Trade #{trade_id} 상세')).to_be_visible()
    expect(page.get_by_text('가격:')).to_be_visible()
    expect(page.get_by_text('수량:')).to_be_visible()
    expect(page.get_by_text('체결시간:')).to_be_visible()

    page.get_by_role('button', name='로그인 화면').click()
    expect(page.get_by_role('heading', name='Non-ferrous Metals Exchange')).to_be_visible()

    assert page_errors == [], f'page errors detected: {page_errors}'
    assert console_errors == [], f'console errors detected: {console_errors}'
    assert api_request_failures == [], f'API request failures detected: {api_request_failures}'
    assert api_response_failures == [], f'API error responses detected: {api_response_failures}'