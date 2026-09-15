import pytest
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import MetalGradeMaster, MetalMaster


def create_master_data():
    with SessionLocal() as db:
        aluminum = MetalMaster(code=' al ', name='Aluminum', status='ACTIVE')
        copper = MetalMaster(code='CU', name='Copper', description='Copper master', status='INACTIVE')
        db.add_all([aluminum, copper])
        db.flush()
        grades = [
            MetalGradeMaster(metal_id=aluminum.id, code=' p1020 ', name='P1020', status='ACTIVE'),
            MetalGradeMaster(metal_id=aluminum.id, code='A356.2', name='A356.2', status='INACTIVE'),
            MetalGradeMaster(metal_id=copper.id, code='P1020', name='Copper P1020', status='ACTIVE'),
        ]
        db.add_all(grades)
        db.commit()
        return aluminum.id, copper.id, grades[0].id


def test_master_read_apis_and_response_schema(client):
    aluminum_id, copper_id, grade_id = create_master_data()

    metals = client.get('/masters/metals')
    assert metals.status_code == 200
    assert [metal['code'] for metal in metals.json()] == ['AL', 'CU']
    assert {metal['status'] for metal in metals.json()} == {'ACTIVE', 'INACTIVE'}

    aluminum = client.get(f'/masters/metals/{aluminum_id}')
    assert aluminum.status_code == 200
    assert set(aluminum.json()) == {
        'id', 'code', 'name', 'description', 'status', 'created_at', 'updated_at'
    }

    grades = client.get(f'/masters/metals/{aluminum_id}/grades')
    assert grades.status_code == 200
    assert [grade['code'] for grade in grades.json()] == ['A356.2', 'P1020']
    assert {grade['status'] for grade in grades.json()} == {'ACTIVE', 'INACTIVE'}

    grade = client.get(f'/masters/grades/{grade_id}')
    assert grade.status_code == 200
    assert grade.json()['metal_id'] == aluminum_id
    assert 'password' not in grade.text.lower()

    assert client.get('/masters/metals/999999').status_code == 404
    assert client.get('/masters/metals/999999/grades').status_code == 404
    assert client.get('/masters/grades/999999').status_code == 404
    assert client.get(f'/masters/metals/{copper_id}').status_code == 200


def test_master_database_constraints_and_foreign_key():
    with SessionLocal() as db:
        aluminum = MetalMaster(code='AL', name='Aluminum')
        copper = MetalMaster(code='CU', name='Copper')
        db.add_all([aluminum, copper])
        db.commit()

        db.add(MetalMaster(code='al', name='Duplicate Aluminum'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(MetalGradeMaster(metal_id=aluminum.id, code='P1020', name='P1020'))
        db.commit()

        db.add(MetalGradeMaster(metal_id=aluminum.id, code='p1020', name='Duplicate P1020'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(MetalGradeMaster(metal_id=copper.id, code='P1020', name='Copper P1020'))
        db.commit()

        db.add(MetalGradeMaster(metal_id=999999, code='ORPHAN', name='Orphan'))
        with pytest.raises(IntegrityError):
            db.commit()


def test_master_status_constraints_and_blank_codes():
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            MetalMaster(code='  ', name='Blank')

        db.add(MetalMaster(code='AL', name='Aluminum', status='DELETED'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        metal = MetalMaster(code='CU', name='Copper')
        db.add(metal)
        db.commit()
        db.add(MetalGradeMaster(metal_id=metal.id, code='C1100', name='C1100', status='DELETED'))
        with pytest.raises(IntegrityError):
            db.commit()


def test_existing_product_contract_is_unchanged(client, seeded_ids):
    products = client.get('/products')
    product = client.get(f"/products/{seeded_ids['product_id']}")
    market = client.get('/market')

    assert products.status_code == 200
    assert product.status_code == 200
    assert market.status_code == 200
    assert set(product.json()) == {
        'seller_id', 'metal', 'grade', 'quantity', 'reserved_quantity',
        'unit', 'price', 'status', 'id', 'created_at',
    }
    assert product.json()['metal'] == 'Aluminum'
    assert product.json()['grade'] == 'A1050'