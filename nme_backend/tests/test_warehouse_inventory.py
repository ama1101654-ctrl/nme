import pytest
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Company, Inventory, MetalGradeMaster, MetalMaster, Product, Warehouse


def login_headers(client):
    response = client.post('/auth/login', json={'email': 'bob@example.com', 'password': 'secret'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def create_warehouse_inventory_data():
    with SessionLocal() as db:
        company = Company(
            company_name='Warehouse Test Company',
            business_registration_number='WAREHOUSE-TEST-001',
            country='KR',
        )
        metal = MetalMaster(code='AL', name='Aluminum')
        db.add_all([company, metal])
        db.flush()
        grade = MetalGradeMaster(metal_id=metal.id, code='P1020', name='P1020')
        warehouse = Warehouse(company_id=company.id, code=' busan-a1 ', name=' Busan A1 ')
        db.add_all([grade, warehouse])
        db.flush()
        inventory = Inventory(
            warehouse_id=warehouse.id,
            metal_id=metal.id,
            grade_id=grade.id,
            quantity=100.5,
            reserved_quantity=20.25,
            unit='TON',
        )
        db.add(inventory)
        db.commit()
        return company.id, warehouse.id, inventory.id


def test_authenticated_warehouse_inventory_read_apis(client):
    company_id, warehouse_id, inventory_id = create_warehouse_inventory_data()
    headers = login_headers(client)

    assert client.get('/warehouses').status_code == 401
    assert client.get('/inventory').status_code == 401

    warehouses = client.get('/warehouses', headers=headers)
    warehouse = client.get(f'/warehouses/{warehouse_id}', headers=headers)
    company_warehouses = client.get(f'/companies/{company_id}/warehouses', headers=headers)
    inventories = client.get('/inventory', headers=headers)
    inventory = client.get(f'/inventory/{inventory_id}', headers=headers)
    warehouse_inventory = client.get(f'/warehouses/{warehouse_id}/inventory', headers=headers)

    assert warehouses.status_code == 200
    assert warehouse.status_code == 200
    assert company_warehouses.status_code == 200
    assert inventories.status_code == 200
    assert inventory.status_code == 200
    assert warehouse_inventory.status_code == 200
    assert warehouse.json()['code'] == 'BUSAN-A1'
    assert warehouse.json()['name'] == 'Busan A1'
    assert inventory.json()['available_quantity'] == pytest.approx(80.25)
    assert inventory.json()['product_id'] is None
    assert set(inventory.json()) == {
        'id', 'warehouse_id', 'metal_id', 'grade_id', 'product_id', 'quantity',
        'reserved_quantity', 'available_quantity', 'unit', 'status', 'created_at', 'updated_at',
    }

    assert client.get('/warehouses/999999', headers=headers).status_code == 404
    assert client.get('/companies/999999/warehouses', headers=headers).status_code == 404
    assert client.get('/inventory/999999', headers=headers).status_code == 404
    assert client.get('/warehouses/999999/inventory', headers=headers).status_code == 404


def test_warehouse_constraints_and_company_foreign_key():
    with SessionLocal() as db:
        company = Company(
            company_name='Warehouse Constraint Company',
            business_registration_number='WAREHOUSE-TEST-002',
            country='KR',
        )
        db.add(company)
        db.commit()
        company_id = company.id

        warehouse = Warehouse(company_id=company_id, code=' wh-a1 ', name='Warehouse A1')
        db.add(warehouse)
        db.commit()
        assert warehouse.code == 'WH-A1'

        db.add(Warehouse(company_id=company_id, code='wh-a1', name='Duplicate'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        with pytest.raises(ValueError):
            Warehouse(company_id=company_id, code=' ', name='Blank Code')
        with pytest.raises(ValueError):
            Warehouse(company_id=company_id, code='WH-B1', name=' ')

        db.add(Warehouse(company_id=999999, code='ORPHAN', name='Orphan'))
        with pytest.raises(IntegrityError):
            db.commit()


@pytest.mark.parametrize(
    ('quantity', 'reserved_quantity'),
    [(-1, 0), (1, -1), (1, 2)],
)
def test_inventory_quantity_constraints(quantity, reserved_quantity):
    with SessionLocal() as db:
        company = Company(
            company_name=f'Quantity Company {quantity} {reserved_quantity}',
            business_registration_number=f'QTY-{quantity}-{reserved_quantity}',
            country='KR',
        )
        db.add(company)
        db.flush()
        warehouse = Warehouse(company_id=company.id, code='QTY-WH', name='Quantity Warehouse')
        db.add(warehouse)
        db.flush()
        db.add(Inventory(
            warehouse_id=warehouse.id,
            quantity=quantity,
            reserved_quantity=reserved_quantity,
            unit='TON',
        ))
        with pytest.raises(IntegrityError):
            db.commit()


def test_inventory_foreign_keys_and_nullable_references():
    with SessionLocal() as db:
        company = Company(
            company_name='Inventory FK Company',
            business_registration_number='WAREHOUSE-TEST-003',
            country='KR',
        )
        db.add(company)
        db.flush()
        warehouse = Warehouse(company_id=company.id, code='FK-WH', name='FK Warehouse')
        db.add(warehouse)
        db.commit()

        inventory = Inventory(warehouse_id=warehouse.id, quantity=0, reserved_quantity=0, unit='TON')
        db.add(inventory)
        db.commit()
        assert inventory.available_quantity == 0
        warehouse_id = warehouse.id

    invalid_values = [
        {'warehouse_id': 999999},
        {'warehouse_id': warehouse_id, 'metal_id': 999999},
        {'warehouse_id': warehouse_id, 'grade_id': 999999},
        {'warehouse_id': warehouse_id, 'product_id': 999999},
    ]
    for values in invalid_values:
        with SessionLocal() as db:
            db.add(Inventory(quantity=1, reserved_quantity=0, unit='TON', **values))
            with pytest.raises(IntegrityError):
                db.commit()


def test_existing_product_contract_and_quantity_are_unchanged(client, seeded_ids):
    with SessionLocal() as db:
        before = db.query(Product).filter(Product.id == seeded_ids['product_id']).one()
        before_values = (before.quantity, before.reserved_quantity)

    product = client.get(f"/products/{seeded_ids['product_id']}")
    market = client.get('/market')

    assert product.status_code == 200
    assert market.status_code == 200
    assert set(product.json()) == {
        'seller_id', 'metal', 'grade', 'quantity', 'reserved_quantity',
        'unit', 'price', 'status', 'id', 'created_at',
    }

    with SessionLocal() as db:
        after = db.query(Product).filter(Product.id == seeded_ids['product_id']).one()
        assert (after.quantity, after.reserved_quantity) == before_values