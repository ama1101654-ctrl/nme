import pytest
from sqlalchemy.exc import IntegrityError

from app import crud
from app.database import SessionLocal
from app.models import Contract, ContractExecution, ContractRevision, Order, Product, Trade, User


def login_headers(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "secret"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_contract_with_active_revision():
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == "bob@example.com").one()
        seller = db.query(User).filter(User.email == "charlie@example.com").one()
        product = db.query(Product).order_by(Product.id.asc()).first()
        buy_order = Order(
            product_id=product.id, buyer_id=buyer.id, quantity=10,
            remaining_quantity=0, price=2500, side="buy", status="FILLED",
        )
        sell_order = Order(
            product_id=product.id, seller_id=seller.id, quantity=10,
            remaining_quantity=0, price=2500, side="sell", status="FILLED",
        )
        db.add_all([buy_order, sell_order])
        db.flush()
        trade = Trade(
            product_id=product.id,
            buy_order_id=buy_order.id,
            sell_order_id=sell_order.id,
            quantity=10,
            price=2500,
        )
        db.add(trade)
        db.flush()
        contract = Contract(
            contract_no=f"NME-CT-2026-{trade.id:010d}",
            trade_id=trade.id,
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=seller.id,
            quantity=10,
            unit=product.unit,
            price=2500,
            currency="KRW",
            total_value=25000,
            status="DRAFT",
            brand="PMB",
            delivery_term="CIF",
            delivery_location="Incheon",
            payment_term="T/T Korean Dollar",
            partial_delivery="YES",
        )
        db.add(contract)
        db.flush()
        revision = ContractRevision(
            contract_id=contract.id,
            revision_no=1,
            revision_status="ACTIVE",
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
        )
        db.add(revision)
        db.commit()
        return contract.id, revision.revision_id, trade.id, product.id


def table_row_snapshot(model, row_id, primary_key="id"):
    with SessionLocal() as db:
        row = db.query(model).filter(getattr(model, primary_key) == row_id).one()
        return tuple(getattr(row, column.name) for column in model.__table__.columns)


@pytest.mark.parametrize("email", ["bob@example.com", "charlie@example.com"])
def test_contract_party_creates_and_reads_execution(client, email):
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    headers = login_headers(client, email)
    response = client.post(f"/contracts/{contract_id}/execution", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] > 0
    assert body["contract_id"] == contract_id
    assert body["contract_revision_id"] == revision_id
    assert body["revision_no"] == 1
    assert body["status"] == "READY"
    assert body["contract_revision"]["revision_status"] == "ACTIVE"
    detail = client.get(f"/contracts/{contract_id}/execution", headers=headers)
    assert detail.status_code == 200
    assert detail.json() == body


def test_execution_creation_preserves_referenced_domain_rows(client):
    contract_id, revision_id, trade_id, product_id = create_contract_with_active_revision()
    contract_before = table_row_snapshot(Contract, contract_id)
    revision_before = table_row_snapshot(ContractRevision, revision_id, "revision_id")
    trade_before = table_row_snapshot(Trade, trade_id)
    product_before = table_row_snapshot(Product, product_id)
    with SessionLocal() as db:
        order_ids = [row.id for row in db.query(Order).filter(
            (Order.id == db.get(Trade, trade_id).buy_order_id)
            | (Order.id == db.get(Trade, trade_id).sell_order_id)
        ).all()]
    orders_before = [table_row_snapshot(Order, order_id) for order_id in order_ids]
    assert client.post(
        f"/contracts/{contract_id}/execution",
        headers=login_headers(client, "bob@example.com"),
    ).status_code == 200
    assert table_row_snapshot(Contract, contract_id) == contract_before
    assert table_row_snapshot(ContractRevision, revision_id, "revision_id") == revision_before
    assert table_row_snapshot(Trade, trade_id) == trade_before
    assert table_row_snapshot(Product, product_id) == product_before
    assert [table_row_snapshot(Order, order_id) for order_id in order_ids] == orders_before


def test_execution_access_policy(client):
    contract_id, _, _, _ = create_contract_with_active_revision()
    path = f"/contracts/{contract_id}/execution"
    assert client.post(path).status_code == 401
    assert client.get(path).status_code == 401
    with SessionLocal() as db:
        db.add(User(company_name="Other", name="Other", email="other@example.com", password="secret", role="BUYER"))
        db.add(User(company_name="Admin", name="Admin", email="admin@example.com", password="secret", role="ADMIN"))
        db.commit()
    assert client.post(path, headers=login_headers(client, "other@example.com")).status_code == 403
    assert client.post(path, headers=login_headers(client, "admin@example.com")).status_code == 403
    assert client.post(path, headers=login_headers(client, "bob@example.com")).status_code == 200
    assert client.get(path, headers=login_headers(client, "other@example.com")).status_code == 403
    assert client.get(path, headers=login_headers(client, "admin@example.com")).status_code == 200


def test_execution_requires_contract_and_active_revision(client):
    headers = login_headers(client, "bob@example.com")
    assert client.post("/contracts/999999/execution", headers=headers).status_code == 404
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    with SessionLocal() as db:
        db.get(ContractRevision, revision_id).revision_status = "DRAFT"
        db.commit()
    assert client.post(f"/contracts/{contract_id}/execution", headers=headers).status_code == 422


def test_duplicate_execution_is_blocked_by_api_and_database(client):
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    headers = login_headers(client, "bob@example.com")
    path = f"/contracts/{contract_id}/execution"
    assert client.post(path, headers=headers).status_code == 200
    assert client.post(path, headers=headers).status_code == 409
    with SessionLocal() as db:
        db.add(ContractExecution(
            contract_id=contract_id,
            contract_revision_id=revision_id,
            status="READY",
        ))
        with pytest.raises(IntegrityError):
            db.commit()


def test_execution_keeps_original_revision_after_later_active_revision(client):
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    headers = login_headers(client, "bob@example.com")
    created = client.post(f"/contracts/{contract_id}/execution", headers=headers).json()
    with SessionLocal() as db:
        original = db.get(ContractRevision, revision_id)
        original.revision_status = "SUPERSEDED"
        values = {
            column.name: getattr(original, column.name)
            for column in ContractRevision.__table__.columns
            if column.name not in {"revision_id", "revision_no", "revision_status", "created_at"}
        }
        later = ContractRevision(revision_no=2, revision_status="ACTIVE", **values)
        db.add(later)
        db.commit()
    detail = client.get(f"/contracts/{contract_id}/execution", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["contract_revision_id"] == created["contract_revision_id"] == revision_id
    assert detail.json()["revision_no"] == 1


def test_execution_uses_approved_proposed_revision(client):
    contract_id, _, _, _ = create_contract_with_active_revision()
    buyer_headers = login_headers(client, "bob@example.com")
    seller_headers = login_headers(client, "charlie@example.com")
    request = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=buyer_headers,
        json={"reason": "Update brand", "brand": "PREMIUM"},
    ).json()
    decision_path = f"/contracts/{contract_id}/change-requests/{request['change_request_id']}/approve"
    assert client.post(decision_path, headers=buyer_headers).status_code == 200
    assert client.post(decision_path, headers=seller_headers).status_code == 200
    execution = client.post(f"/contracts/{contract_id}/execution", headers=buyer_headers)
    assert execution.status_code == 200
    assert execution.json()["contract_revision_id"] == request["proposed_revision_id"]
    assert execution.json()["contract_revision"]["brand"] == "PREMIUM"


def test_unapproved_proposed_active_revision_is_rejected(client):
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    request = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=login_headers(client, "bob@example.com"),
        json={"reason": "Pending", "brand": "PENDING BRAND"},
    ).json()
    with SessionLocal() as db:
        db.get(ContractRevision, revision_id).revision_status = "SUPERSEDED"
        db.get(ContractRevision, request["proposed_revision_id"]).revision_status = "ACTIVE"
        db.commit()
    response = client.post(
        f"/contracts/{contract_id}/execution",
        headers=login_headers(client, "charlie@example.com"),
    )
    assert response.status_code == 409


def test_pending_change_request_blocks_execution_of_previous_active_revision(client):
    contract_id, _, _, _ = create_contract_with_active_revision()
    headers = login_headers(client, "bob@example.com")
    created = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "Pending approval", "delivery_location": "Busan"},
    )
    assert created.status_code == 200
    response = client.post(f"/contracts/{contract_id}/execution", headers=headers)
    assert response.status_code == 409
    with SessionLocal() as db:
        assert db.query(ContractExecution).count() == 0


def test_forced_execution_failure_rolls_back_insert(client, monkeypatch):
    contract_id, _, _, _ = create_contract_with_active_revision()
    original = crud.create_contract_execution

    def fail_after_staging(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("forced execution failure")

    monkeypatch.setattr(crud, "create_contract_execution", fail_after_staging)
    with pytest.raises(RuntimeError, match="forced execution failure"):
        client.post(
            f"/contracts/{contract_id}/execution",
            headers=login_headers(client, "bob@example.com"),
        )
    with SessionLocal() as db:
        assert db.query(ContractExecution).count() == 0