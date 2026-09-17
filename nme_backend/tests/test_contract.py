import threading

import pytest
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Contract, Inventory, Order, Product, Trade, User


def login_headers(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def create_trade_graph(quantity=40, price=2500):
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == 'bob@example.com').one()
        seller = db.query(User).filter(User.email == 'charlie@example.com').one()
        product = db.query(Product).order_by(Product.id.asc()).first()
        assert product is not None
        buy_order = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=quantity,
            remaining_quantity=0,
            price=price + 100,
            side='buy',
            status='FILLED',
        )
        sell_order = Order(
            product_id=product.id,
            seller_id=seller.id,
            quantity=quantity,
            remaining_quantity=0,
            price=price,
            side='sell',
            status='FILLED',
        )
        db.add_all([buy_order, sell_order])
        db.flush()
        trade = Trade(
            product_id=product.id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            quantity=quantity,
            price=price,
        )
        db.add(trade)
        db.commit()
        return trade.id, buy_order.id, sell_order.id, product.id


def row_snapshot(model, row_id):
    with SessionLocal() as db:
        row = db.query(model).filter(model.id == row_id).one()
        return tuple(getattr(row, column.name) for column in model.__table__.columns)


def inventory_snapshot():
    with SessionLocal() as db:
        return [
            tuple(getattr(row, column.name) for column in Inventory.__table__.columns)
            for row in db.query(Inventory).order_by(Inventory.id).all()
        ]


def test_contract_snapshot_is_server_derived_and_sources_are_unchanged(client):
    trade_id, buy_order_id, sell_order_id, product_id = create_trade_graph()
    before = {
        'trade': row_snapshot(Trade, trade_id),
        'buy': row_snapshot(Order, buy_order_id),
        'sell': row_snapshot(Order, sell_order_id),
        'product': row_snapshot(Product, product_id),
        'inventory': inventory_snapshot(),
    }

    response = client.post(
        f'/trades/{trade_id}/contract',
        json={'buyer_id': 999999, 'seller_id': 999999, 'total_value': 1},
        headers=login_headers(client, 'bob@example.com'),
    )

    assert response.status_code == 200
    body = response.json()
    assert body['trade_id'] == trade_id
    assert body['product_id'] == product_id
    assert body['quantity'] == 40
    assert body['unit'] == 'TON'
    assert body['price'] == 2500
    assert body['currency'] == 'KRW'
    assert body['total_value'] == 100000
    assert body['status'] == 'DRAFT'
    assert body['brand'] is None
    assert body['tolerance'] is None
    assert body['quotation_period'] is None
    assert body['delivery_term'] is None
    assert body['delivery_location'] is None
    assert body['payment_term'] is None
    assert body['partial_delivery'] is None
    assert body['buyer_id'] != 999999
    assert body['seller_id'] != 999999
    assert body['contract_no'].startswith('NME-CT-')
    assert row_snapshot(Trade, trade_id) == before['trade']
    assert row_snapshot(Order, buy_order_id) == before['buy']
    assert row_snapshot(Order, sell_order_id) == before['sell']
    assert row_snapshot(Product, product_id) == before['product']
    assert inventory_snapshot() == before['inventory']


def test_contract_terms_snapshot_is_returned_by_all_get_apis(client):
    trade_id, buy_order_id, sell_order_id, product_id = create_trade_graph()
    headers = login_headers(client, 'bob@example.com')
    terms = {
        'brand': 'PMB',
        'tolerance': '+/-2%',
        'quotation_period': 'Unknown On Day',
        'delivery_term': 'CIF',
        'delivery_location': 'Incheon',
        'payment_term': 'T/T Korean Dollar',
        'partial_delivery': 'YES',
    }
    with SessionLocal() as db:
        trade = db.query(Trade).filter(Trade.id == trade_id).one()
        buy_order = db.query(Order).filter(Order.id == buy_order_id).one()
        sell_order = db.query(Order).filter(Order.id == sell_order_id).one()
        contract = Contract(
            contract_no=f'NME-CT-{trade.created_at.year}-{trade.id:010d}',
            trade_id=trade.id,
            product_id=product_id,
            buyer_id=buy_order.buyer_id,
            seller_id=sell_order.seller_id,
            quantity=trade.quantity,
            unit='TON',
            price=trade.price,
            currency='KRW',
            total_value=trade.quantity * trade.price,
            status='DRAFT',
            **terms,
        )
        db.add(contract)
        db.commit()
        contract_id = contract.id

    detail = client.get(f'/contracts/{contract_id}', headers=headers)
    trade_detail = client.get(f'/trades/{trade_id}/contract', headers=headers)
    listing = client.get('/contracts', headers=headers)
    assert detail.status_code == 200
    assert trade_detail.status_code == 200
    assert listing.status_code == 200
    for key, value in terms.items():
        assert detail.json()[key] == value
        assert trade_detail.json()[key] == value
        assert listing.json()[0][key] == value


def test_contract_auth_visibility_duplicate_and_missing_resources(client):
    trade_id, _, _, _ = create_trade_graph()
    buyer_headers = login_headers(client, 'bob@example.com')
    seller_headers = login_headers(client, 'charlie@example.com')
    admin_headers = login_headers(client, 'alice@example.com')
    created = client.post(f'/trades/{trade_id}/contract', headers=buyer_headers)
    assert created.status_code == 200
    contract_id = created.json()['id']

    assert client.post(f'/trades/{trade_id}/contract', headers=seller_headers).status_code == 409
    assert client.get('/contracts').status_code == 401
    assert client.get('/contracts', headers=buyer_headers).json()[0]['id'] == contract_id
    assert client.get('/contracts', headers=seller_headers).json()[0]['id'] == contract_id
    assert client.get('/contracts', headers=admin_headers).json()[0]['id'] == contract_id
    assert client.get(f'/contracts/{contract_id}', headers=buyer_headers).status_code == 200
    assert client.get(f'/trades/{trade_id}/contract', headers=seller_headers).status_code == 200
    assert client.post(f'/trades/{trade_id + 999999}/contract', headers=buyer_headers).status_code == 404
    assert client.get(f'/contracts/{contract_id + 999999}', headers=buyer_headers).status_code == 404

    with SessionLocal() as db:
        db.add(User(company_name='Other', name='Other', email='other@example.com', password='secret', role='BUYER'))
        db.commit()
    outsider_headers = login_headers(client, 'other@example.com')
    assert client.get('/contracts', headers=outsider_headers).json() == []
    assert client.get(f'/contracts/{contract_id}', headers=outsider_headers).status_code == 403
    assert client.get(f'/trades/{trade_id}/contract', headers=outsider_headers).status_code == 403
    assert client.post(f'/trades/{trade_id}/contract', headers=outsider_headers).status_code == 403

    admin_trade_id, _, _, _ = create_trade_graph(quantity=5, price=3000)
    assert client.post(f'/trades/{admin_trade_id}/contract', headers=admin_headers).status_code == 200


@pytest.mark.parametrize(
    'mutation',
    [
        {'buy_order_id': 999999},
        {'sell_order_id': 999999},
        {'product_id': 999999},
        {'quantity': 0},
        {'price': 0},
    ],
)
def test_invalid_trade_graph_returns_422_and_rolls_back(client, mutation):
    trade_id, _, _, _ = create_trade_graph()
    with SessionLocal() as db:
        trade = db.query(Trade).filter(Trade.id == trade_id).one()
        for key, value in mutation.items():
            setattr(trade, key, value)
        db.commit()

    response = client.post(
        f'/trades/{trade_id}/contract',
        headers=login_headers(client, 'alice@example.com'),
    )

    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(Contract).count() == 0


def test_mismatched_order_product_returns_422_and_rolls_back(client):
    trade_id, buy_order_id, _, _ = create_trade_graph()
    with SessionLocal() as db:
        buy_order = db.query(Order).filter(Order.id == buy_order_id).one()
        product = Product(
            seller_id=buy_order.buyer_id,
            metal='Copper',
            grade='C1100',
            quantity=1,
            reserved_quantity=0,
            unit='TON',
            price=1,
            status='available',
        )
        db.add(product)
        db.flush()
        buy_order.product_id = product.id
        db.commit()

    response = client.post(
        f'/trades/{trade_id}/contract',
        headers=login_headers(client, 'alice@example.com'),
    )

    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(Contract).count() == 0


def test_concurrent_contract_creation_has_one_success_and_one_conflict(client):
    trade_id, _, _, _ = create_trade_graph()
    headers = login_headers(client, 'bob@example.com')
    barrier = threading.Barrier(2)
    statuses = []

    def create_contract():
        barrier.wait()
        statuses.append(client.post(f'/trades/{trade_id}/contract', headers=headers).status_code)

    threads = [threading.Thread(target=create_contract) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 409]
    with SessionLocal() as db:
        assert db.query(Contract).filter(Contract.trade_id == trade_id).count() == 1


def test_contract_database_foreign_key_unique_and_check_constraints():
    trade_id, _, _, product_id = create_trade_graph()
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == 'bob@example.com').one()
        seller = db.query(User).filter(User.email == 'charlie@example.com').one()
        valid_values = {
            'trade_id': trade_id,
            'product_id': product_id,
            'buyer_id': buyer.id,
            'seller_id': seller.id,
            'quantity': 1,
            'unit': 'TON',
            'price': 1,
            'currency': 'KRW',
            'total_value': 1,
            'status': 'DRAFT',
        }

    invalid_overrides = [
        {'trade_id': 999999},
        {'product_id': 999999},
        {'buyer_id': 999999},
        {'quantity': 0},
        {'unit': ' '},
        {'price': 0},
        {'currency': ' '},
        {'total_value': 0},
        {'status': 'UNKNOWN'},
        {'brand': ' '},
        {'brand': 'B' * 101},
        {'tolerance': ' '},
        {'quotation_period': 'Q' * 201},
        {'delivery_term': ' '},
        {'delivery_location': 'L' * 201},
        {'payment_term': ' '},
        {'partial_delivery': 'MAYBE'},
    ]
    for index, overrides in enumerate(invalid_overrides):
        with SessionLocal() as db:
            db.add(Contract(contract_no=f'INVALID-{index}', **(valid_values | overrides)))
            with pytest.raises(IntegrityError):
                db.commit()

    with SessionLocal() as db:
        db.add(Contract(contract_no='UNIQUE-A', **valid_values))
        db.commit()
    with SessionLocal() as db:
        db.add(Contract(contract_no='UNIQUE-B', **valid_values))
        with pytest.raises(IntegrityError):
            db.commit()


def test_contract_response_schema_is_exact(client):
    trade_id, _, _, _ = create_trade_graph()
    response = client.post(
        f'/trades/{trade_id}/contract',
        headers=login_headers(client, 'bob@example.com'),
    )
    assert response.status_code == 200
    expected_fields = {
        'id', 'contract_no', 'trade_id', 'product_id', 'buyer_id', 'seller_id',
        'quantity', 'unit', 'price', 'currency', 'total_value', 'status',
        'brand', 'tolerance', 'quotation_period', 'delivery_term',
        'delivery_location', 'payment_term', 'partial_delivery',
        'created_at', 'updated_at',
    }
    assert set(response.json()) == expected_fields
    spec = client.get('/openapi.json').json()
    assert set(spec['components']['schemas']['ContractResponse']['properties']) == expected_fields
