from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app import crud
from app.database import SessionLocal
from app.models import ContractExecution, ContractRevision, ExecutionMilestone, User
from test_contract_execution import create_contract_with_active_revision, login_headers


def create_execution(client):
    contract_id, revision_id, _, _ = create_contract_with_active_revision()
    response = client.post(
        f"/contracts/{contract_id}/execution",
        headers=login_headers(client, "bob@example.com"),
    )
    assert response.status_code == 200
    return response.json()["execution_id"], revision_id


def initialize_milestones(client, execution_id, email="bob@example.com"):
    return client.post(
        f"/executions/{execution_id}/milestones",
        headers=login_headers(client, email),
    )


def test_party_initializes_and_reads_default_milestones(client):
    execution_id, _ = create_execution(client)
    with SessionLocal() as db:
        assert db.query(ExecutionMilestone).count() == 0
    created = initialize_milestones(client, execution_id)
    assert created.status_code == 200
    body = created.json()
    assert [item["milestone_code"] for item in body] == [code for code, _ in crud.DEFAULT_EXECUTION_MILESTONES]
    assert body[0]["status"] == "READY"
    assert all(item["status"] == "PENDING" for item in body[1:])
    assert all(item["completed_at"] is None for item in body)

    listing = client.get(
        f"/executions/{execution_id}/milestones",
        headers=login_headers(client, "charlie@example.com"),
    )
    detail = client.get(
        f"/executions/{execution_id}/milestones/{body[0]['milestone_id']}",
        headers=login_headers(client, "charlie@example.com"),
    )
    assert listing.status_code == 200
    assert listing.json() == body
    assert detail.status_code == 200
    assert detail.json() == body[0]


def test_milestone_access_policy_and_admin_read_only(client):
    execution_id, _ = create_execution(client)
    path = f"/executions/{execution_id}/milestones"
    assert client.get(path).status_code == 401
    assert client.post(path).status_code == 401
    with SessionLocal() as db:
        db.add(User(company_name="Other", name="Other", email="other@example.com", password="secret", role="BUYER"))
        db.commit()
    other = login_headers(client, "other@example.com")
    admin = login_headers(client, "alice@example.com")
    assert client.get(path, headers=other).status_code == 403
    assert client.post(path, headers=other).status_code == 403
    assert client.post(path, headers=admin).status_code == 403
    assert initialize_milestones(client, execution_id, "charlie@example.com").status_code == 200
    assert client.get(path, headers=admin).status_code == 200
    milestone_id = client.get(path, headers=admin).json()[1]["milestone_id"]
    assert client.patch(
        f"{path}/{milestone_id}",
        headers=admin,
        json={"status": "READY"},
    ).status_code == 403


def test_milestone_validation_unique_and_foreign_key_constraints(client):
    execution_id, _ = create_execution(client)
    path = f"/executions/{execution_id}/milestones"
    headers = login_headers(client, "bob@example.com")
    assert client.post(path, headers=headers, json={"milestone_code": "UNKNOWN"}).status_code == 422
    assert client.post(
        path,
        headers=headers,
        json={"milestone_code": "PAYMENT_READY", "status": "UNKNOWN"},
    ).status_code == 422
    assert initialize_milestones(client, execution_id).status_code == 200
    assert initialize_milestones(client, execution_id).status_code == 409
    with SessionLocal() as db:
        invalid_rows = [
            ExecutionMilestone(execution_id=execution_id, milestone_code="UNKNOWN", status="PENDING"),
            ExecutionMilestone(execution_id=execution_id, milestone_code="PAYMENT_READY", status="UNKNOWN"),
            ExecutionMilestone(execution_id=execution_id, milestone_code="PAYMENT_READY", status="PENDING"),
            ExecutionMilestone(execution_id=999999, milestone_code="PAYMENT_READY", status="PENDING"),
            ExecutionMilestone(
                execution_id=execution_id,
                milestone_code="PAYMENT_READY",
                status="READY",
                completed_at=datetime.now(timezone.utc),
            ),
            ExecutionMilestone(
                execution_id=execution_id,
                milestone_code="PAYMENT_READY",
                status="COMPLETED",
            ),
            ExecutionMilestone(
                execution_id=execution_id,
                milestone_code="PAYMENT_READY",
                status="PENDING",
                note=" ",
            ),
        ]
        for row in invalid_rows:
            db.add(row)
            with pytest.raises(IntegrityError):
                db.commit()
            db.rollback()


def test_milestone_state_transition_and_completed_at_consistency(client):
    execution_id, _ = create_execution(client)
    milestones = initialize_milestones(client, execution_id).json()
    payment = next(item for item in milestones if item["milestone_code"] == "PAYMENT_READY")
    path = f"/executions/{execution_id}/milestones/{payment['milestone_id']}"
    headers = login_headers(client, "bob@example.com")
    assert client.patch(path, headers=headers, json={"status": "COMPLETED"}).status_code == 409
    assert client.patch(path, headers=headers, json={"status": "UNKNOWN"}).status_code == 422
    ready = client.patch(path, headers=headers, json={"status": "READY", "note": "Payment documents ready"})
    assert ready.status_code == 200
    assert ready.json()["completed_at"] is None
    completed = client.patch(path, headers=headers, json={"status": "COMPLETED", "note": "Readiness recorded"})
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    assert client.patch(path, headers=headers, json={"status": "READY"}).status_code == 409


def test_milestone_initialization_rolls_back_on_failure(client, monkeypatch):
    execution_id, _ = create_execution(client)
    original = crud.create_default_execution_milestones

    def fail_after_staging(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("forced milestone failure")

    monkeypatch.setattr(crud, "create_default_execution_milestones", fail_after_staging)
    with pytest.raises(RuntimeError, match="forced milestone failure"):
        initialize_milestones(client, execution_id)
    with SessionLocal() as db:
        assert db.query(ExecutionMilestone).count() == 0


def test_milestones_do_not_change_execution_revision_reference(client):
    execution_id, revision_id = create_execution(client)
    assert initialize_milestones(client, execution_id).status_code == 200
    with SessionLocal() as db:
        execution = db.get(ContractExecution, execution_id)
        original = db.get(ContractRevision, revision_id)
        original.revision_status = "SUPERSEDED"
        values = {
            column.name: getattr(original, column.name)
            for column in ContractRevision.__table__.columns
            if column.name not in {"revision_id", "revision_no", "revision_status", "created_at"}
        }
        db.add(ContractRevision(revision_no=2, revision_status="ACTIVE", **values))
        db.commit()
        db.refresh(execution)
        assert execution.contract_revision_id == revision_id