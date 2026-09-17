from app.database import SessionLocal
from app.models import Contract, ContractChangeRequest, ContractRevision, Order, Product, Trade, User


TERMS = (
    "brand",
    "tolerance",
    "quotation_period",
    "delivery_term",
    "delivery_location",
    "payment_term",
    "partial_delivery",
)


def login_headers(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "secret"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_contract_with_revision():
    with SessionLocal() as db:
        buyer = db.query(User).filter(User.email == "bob@example.com").one()
        seller = db.query(User).filter(User.email == "charlie@example.com").one()
        product = db.query(Product).order_by(Product.id.asc()).first()
        buy_order = Order(
            product_id=product.id,
            buyer_id=buyer.id,
            quantity=10,
            remaining_quantity=0,
            price=2500,
            side="buy",
            status="FILLED",
        )
        sell_order = Order(
            product_id=product.id,
            seller_id=seller.id,
            quantity=10,
            remaining_quantity=0,
            price=2500,
            side="sell",
            status="FILLED",
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
            brand="CONTRACT BRAND",
            tolerance="+/-2%",
            quotation_period="Unknown On Day",
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
            brand="BASE BRAND",
            tolerance=contract.tolerance,
            quotation_period=contract.quotation_period,
            delivery_term=contract.delivery_term,
            delivery_location=contract.delivery_location,
            payment_term=contract.payment_term,
            partial_delivery=contract.partial_delivery,
        )
        db.add(revision)
        db.commit()
        return contract.id, revision.revision_id


def row_snapshot(model, row_id):
    with SessionLocal() as db:
        row = db.query(model).filter(model.id == row_id).one()
        return tuple(getattr(row, column.name) for column in model.__table__.columns)


def test_create_change_request_copies_base_and_applies_only_terms(client):
    contract_id, base_revision_id = create_contract_with_revision()
    contract_before = row_snapshot(Contract, contract_id)
    response = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=login_headers(client, "bob@example.com"),
        json={"reason": "Update delivery", "brand": "PROPOSED BRAND", "delivery_location": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["base_revision_id"] == base_revision_id
    assert body["base_revision_no"] == 1
    assert body["proposed_revision_no"] == 2
    assert body["proposed_revision_status"] == "DRAFT"
    assert body["requested_by"] > 0
    assert body["base_revision"]["brand"] == "BASE BRAND"
    assert body["proposed_revision"]["brand"] == "PROPOSED BRAND"
    assert body["proposed_revision"]["delivery_location"] is None
    assert body["proposed_revision"]["payment_term"] == "T/T Korean Dollar"
    assert body["proposed_revision"]["price"] == body["base_revision"]["price"]
    assert row_snapshot(Contract, contract_id) == contract_before

    with SessionLocal() as db:
        base = db.query(ContractRevision).filter(ContractRevision.revision_id == base_revision_id).one()
        assert base.brand == "BASE BRAND"
        assert db.query(ContractChangeRequest).count() == 1
        assert db.query(ContractRevision).filter(ContractRevision.contract_id == contract_id).count() == 2


def test_forbidden_commercial_fields_are_rejected_without_rows(client):
    contract_id, _ = create_contract_with_revision()
    headers = login_headers(client, "bob@example.com")
    for forbidden_field in ("price", "quantity", "product_id", "buyer_id", "seller_id", "trade_id", "total_value"):
        response = client.post(
            f"/contracts/{contract_id}/change-requests",
            headers=headers,
            json={"reason": "Invalid request", forbidden_field: 1},
        )
        assert response.status_code == 422
    with SessionLocal() as db:
        assert db.query(ContractChangeRequest).count() == 0
        assert db.query(ContractRevision).filter(ContractRevision.contract_id == contract_id).count() == 1


def test_blank_reason_and_invalid_terms_are_rejected(client):
    contract_id, _ = create_contract_with_revision()
    headers = login_headers(client, "bob@example.com")
    assert client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "   ", "brand": "new"},
    ).status_code == 422
    assert client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "Valid", "partial_delivery": "MAYBE"},
    ).status_code == 422


def test_second_pending_request_is_409_and_creates_no_revision(client):
    contract_id, _ = create_contract_with_revision()
    headers = login_headers(client, "bob@example.com")
    first = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "First", "brand": "NEW"},
    )
    second = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "Second", "tolerance": "+/-5%"},
    )
    assert first.status_code == 200
    assert second.status_code == 409
    with SessionLocal() as db:
        assert db.query(ContractChangeRequest).count() == 1
        assert db.query(ContractRevision).filter(ContractRevision.contract_id == contract_id).count() == 2


def test_list_and_detail_return_read_only_comparison(client):
    contract_id, _ = create_contract_with_revision()
    headers = login_headers(client, "charlie@example.com")
    created = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=headers,
        json={"reason": "Payment update", "payment_term": "L/C"},
    ).json()
    listing = client.get(f"/contracts/{contract_id}/change-requests", headers=headers)
    detail = client.get(
        f"/contracts/{contract_id}/change-requests/{created['change_request_id']}",
        headers=headers,
    )
    assert listing.status_code == 200
    assert listing.json()[0]["change_request_id"] == created["change_request_id"]
    assert detail.status_code == 200
    assert detail.json()["base_revision"]["payment_term"] == "T/T Korean Dollar"
    assert detail.json()["proposed_revision"]["payment_term"] == "L/C"
    for term in TERMS:
        assert term in detail.json()["base_revision"]
        assert term in detail.json()["proposed_revision"]


def test_change_request_access_and_missing_resources(client):
    contract_id, _ = create_contract_with_revision()
    path = f"/contracts/{contract_id}/change-requests"
    assert client.post(path, json={"reason": "No auth"}).status_code == 401
    assert client.get(path).status_code == 401

    with SessionLocal() as db:
        db.add(User(company_name="Other", name="Other", email="other@example.com", password="secret", role="BUYER"))
        db.commit()
    other_headers = login_headers(client, "other@example.com")
    assert client.post(path, headers=other_headers, json={"reason": "Forbidden"}).status_code == 403
    assert client.get(path, headers=other_headers).status_code == 403

    buyer_headers = login_headers(client, "bob@example.com")
    assert client.get("/contracts/999999/change-requests", headers=buyer_headers).status_code == 404
    assert client.get(f"{path}/999999", headers=buyer_headers).status_code == 404


def test_change_request_requires_existing_base_revision(client):
    contract_id, revision_id = create_contract_with_revision()
    with SessionLocal() as db:
        db.query(ContractRevision).filter(ContractRevision.revision_id == revision_id).delete()
        db.commit()
    response = client.post(
        f"/contracts/{contract_id}/change-requests",
        headers=login_headers(client, "bob@example.com"),
        json={"reason": "No base", "brand": "NEW"},
    )
    assert response.status_code == 422