import pytest
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Contract, ContractRevision, Order, Product, Trade, User


SNAPSHOT_FIELDS = {
    'contract_no', 'trade_id', 'product_id', 'buyer_id', 'seller_id',
    'quantity', 'unit', 'price', 'currency', 'total_value', 'status',
    'brand', 'tolerance', 'quotation_period', 'delivery_term',
    'delivery_location', 'payment_term', 'partial_delivery',
}


def login_headers(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def create_contract_snapshot(quantity=10, price=2500):
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == 'bob@example.com').one()
        seller = db.query(User).filter(User.email == 'charlie@example.com').one()
        product = db.query(Product).order_by(Product.id.asc()).first()
        buy_order = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=quantity,
            remaining_quantity=0,
            price=price,
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
        db.flush()
        contract = Contract(
            contract_no=f'NME-CT-2026-{trade.id:010d}',
            trade_id=trade.id,
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            quantity=quantity,
            unit=product.unit,
            price=price,
            currency='KRW',
            total_value=quantity * price,
            status='DRAFT',
            brand='PMB',
            tolerance='+/-2%',
            quotation_period='Unknown On Day',
            delivery_term='CIF',
            delivery_location='Incheon',
            payment_term='T/T Korean Dollar',
            partial_delivery='YES',
        )
        db.add(contract)
        db.commit()
        return contract.id


def revision_snapshot(revision):
    return {field: revision[field] for field in SNAPSHOT_FIELDS}


def contract_row_snapshot(contract_id):
    with SessionLocal() as db:
        contract = db.query(Contract).filter(Contract.id == contract_id).one()
        return tuple(getattr(contract, column.name) for column in Contract.__table__.columns)


def test_revision_one_starts_at_one(client):
    contract_id = create_contract_snapshot()
    contract_before = contract_row_snapshot(contract_id)
    response = client.post(
        f'/contracts/{contract_id}/revisions',
        json={'buyer_id': 999999, 'total_value': 1, 'brand': 'CLIENT VALUE'},
        headers=login_headers(client, 'bob@example.com'),
    )
    assert response.status_code == 200
    assert response.json()['revision_no'] == 1
    assert response.json()['revision_status'] == 'DRAFT'
    assert response.json()['buyer_id'] != 999999
    assert response.json()['total_value'] == 25000
    assert response.json()['brand'] == 'PMB'
    assert contract_row_snapshot(contract_id) == contract_before


def test_revision_two_increments_per_contract(client):
    contract_id = create_contract_snapshot()
    headers = login_headers(client, 'bob@example.com')
    first = client.post(f'/contracts/{contract_id}/revisions', headers=headers)
    second = client.post(f'/contracts/{contract_id}/revisions', headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()['revision_no'] == 2
    assert revision_snapshot(second.json()) == revision_snapshot(first.json())


def test_revisions_are_distinct_rows(client):
    contract_id = create_contract_snapshot()
    headers = login_headers(client, 'bob@example.com')
    first = client.post(f'/contracts/{contract_id}/revisions', headers=headers).json()
    second = client.post(f'/contracts/{contract_id}/revisions', headers=headers).json()
    assert first['revision_id'] != second['revision_id']


def test_revision_one_remains_immutable_after_revision_two(client):
    contract_id = create_contract_snapshot()
    headers = login_headers(client, 'bob@example.com')
    first = client.post(f'/contracts/{contract_id}/revisions', headers=headers).json()
    original_snapshot = revision_snapshot(first)
    client.post(f'/contracts/{contract_id}/revisions', headers=headers)
    reloaded = client.get(
        f"/contracts/{contract_id}/revisions/{first['revision_id']}",
        headers=headers,
    )
    assert reloaded.status_code == 200
    assert revision_snapshot(reloaded.json()) == original_snapshot


def test_duplicate_revision_number_is_rejected_by_database(client):
    contract_id = create_contract_snapshot()
    headers = login_headers(client, 'bob@example.com')
    created = client.post(f'/contracts/{contract_id}/revisions', headers=headers).json()
    duplicate_values = revision_snapshot(created) | {
        'contract_id': contract_id,
        'revision_no': created['revision_no'],
        'revision_status': 'DRAFT',
    }
    with SessionLocal() as db:
        db.add(ContractRevision(**duplicate_values))
        with pytest.raises(IntegrityError):
            db.commit()


def test_each_contract_starts_revision_number_at_one(client):
    first_contract_id = create_contract_snapshot(quantity=5, price=2000)
    second_contract_id = create_contract_snapshot(quantity=6, price=2100)
    headers = login_headers(client, 'bob@example.com')
    first = client.post(f'/contracts/{first_contract_id}/revisions', headers=headers)
    second = client.post(f'/contracts/{second_contract_id}/revisions', headers=headers)
    assert first.json()['revision_no'] == 1
    assert second.json()['revision_no'] == 1


def test_revision_requires_authentication(client):
    contract_id = create_contract_snapshot()
    assert client.post(f'/contracts/{contract_id}/revisions').status_code == 401
    assert client.get(f'/contracts/{contract_id}/revisions').status_code == 401


def test_unrelated_user_cannot_create_or_read_revisions(client):
    contract_id = create_contract_snapshot()
    with SessionLocal() as db:
        db.add(User(company_name='Other', name='Other', email='other@example.com', password='secret', role='BUYER'))
        db.commit()
    headers = login_headers(client, 'other@example.com')
    assert client.post(f'/contracts/{contract_id}/revisions', headers=headers).status_code == 403
    assert client.get(f'/contracts/{contract_id}/revisions', headers=headers).status_code == 403


def test_missing_contract_returns_404(client):
    headers = login_headers(client, 'bob@example.com')
    assert client.post('/contracts/999999/revisions', headers=headers).status_code == 404
    assert client.get('/contracts/999999/revisions', headers=headers).status_code == 404


def test_revision_detail_returns_complete_server_snapshot(client):
    contract_id = create_contract_snapshot()
    headers = login_headers(client, 'charlie@example.com')
    created = client.post(f'/contracts/{contract_id}/revisions', headers=headers)
    detail = client.get(
        f"/contracts/{contract_id}/revisions/{created.json()['revision_id']}",
        headers=headers,
    )
    listing = client.get(f'/contracts/{contract_id}/revisions', headers=headers)
    assert detail.status_code == 200
    assert SNAPSHOT_FIELDS.issubset(detail.json())
    assert detail.json()['brand'] == 'PMB'
    assert detail.json()['payment_term'] == 'T/T Korean Dollar'
    assert detail.json()['partial_delivery'] == 'YES'
    assert listing.status_code == 200
    assert set(listing.json()[0]) == {
        'revision_id', 'contract_id', 'revision_no', 'revision_status', 'created_at',
    }
    assert detail.json()['contract_id'] == contract_id
    assert client.get(
        f"/contracts/{contract_id}/revisions/{created.json()['revision_id'] + 999999}",
        headers=headers,
    ).status_code == 404
