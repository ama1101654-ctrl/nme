from datetime import datetime

import pytest
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, inspect, select
from sqlalchemy.exc import IntegrityError

from app.database import Base, SessionLocal
from app.models import Company, CompanyMember, InvestorProfile, MemberProfile, User


def login(client, email):
    response = client.post('/auth/login', json={'email': email, 'password': 'secret'})
    assert response.status_code == 200
    return response.json()


def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


def test_existing_user_login_and_empty_member_profile(client):
    buyer = login(client, 'bob@example.com')
    response = client.get('/members/me', headers=auth_headers(buyer['access_token']))

    assert response.status_code == 200
    assert response.json() == {
        'user_id': buyer['user_id'],
        'member_type': None,
        'display_name': None,
        'status': None,
        'companies': [],
        'investor_profile': None,
    }


@pytest.mark.parametrize('trading_role', ['BUYER', 'SELLER', 'BOTH'])
def test_company_member_profile_and_trading_roles(client, trading_role):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'bob@example.com').one()
        company = Company(
            company_name=f'{trading_role} Metals',
            business_registration_number=f'BRN-{trading_role}',
            country='KR',
        )
        db.add_all([
            company,
            MemberProfile(user_id=user.id, member_type='COMPANY', display_name=user.name),
        ])
        db.flush()
        db.add(CompanyMember(company_id=company.id, user_id=user.id, trading_role=trading_role))
        db.commit()

    buyer = login(client, 'bob@example.com')
    response = client.get('/members/me', headers=auth_headers(buyer['access_token']))

    assert response.status_code == 200
    payload = response.json()
    assert payload['member_type'] == 'COMPANY'
    assert payload['companies'] == [{
        'company_id': payload['companies'][0]['company_id'],
        'company_name': f'{trading_role} Metals',
        'trading_role': trading_role,
        'status': 'ACTIVE',
    }]


def test_investor_and_search_member_profiles(client):
    with SessionLocal() as db:
        investor = db.query(User).filter(User.email == 'bob@example.com').one()
        search_member = db.query(User).filter(User.email == 'charlie@example.com').one()
        db.add_all([
            MemberProfile(user_id=investor.id, member_type='INVESTOR', display_name='NME Investor'),
            InvestorProfile(
                user_id=investor.id,
                investor_type='INDIVIDUAL',
                display_name='NME Investor',
                country='KR',
            ),
            MemberProfile(user_id=search_member.id, member_type='SEARCH', display_name='Market Researcher'),
        ])
        db.commit()

    investor_login = login(client, 'bob@example.com')
    investor_response = client.get('/members/me', headers=auth_headers(investor_login['access_token']))
    assert investor_response.status_code == 200
    assert investor_response.json()['member_type'] == 'INVESTOR'
    assert investor_response.json()['investor_profile']['investor_type'] == 'INDIVIDUAL'

    search_login = login(client, 'charlie@example.com')
    search_response = client.get('/members/me', headers=auth_headers(search_login['access_token']))
    assert search_response.status_code == 200
    assert search_response.json()['member_type'] == 'SEARCH'
    assert search_response.json()['companies'] == []
    assert search_response.json()['investor_profile'] is None


def test_member_constraints_prevent_duplicate_profiles_and_memberships():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'bob@example.com').one()
        db.add(MemberProfile(user_id=user.id, member_type='COMPANY'))
        db.commit()

        db.add(MemberProfile(user_id=user.id, member_type='SEARCH'))
        with pytest.raises(IntegrityError):
            db.commit()


def test_member_constraints_reject_invalid_business_values():
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == 'bob@example.com').one()
        db.add(MemberProfile(user_id=user.id, member_type='UNKNOWN'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(InvestorProfile(user_id=user.id, investor_type='FUND'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        company = Company(
            company_name='Invalid Role Metals',
            business_registration_number='BRN-INVALID-ROLE',
            country='KR',
        )
        db.add(company)
        db.flush()
        db.add(CompanyMember(company_id=company.id, user_id=user.id, trading_role='OBSERVER'))
        with pytest.raises(IntegrityError):
            db.commit()


def test_company_registration_and_foreign_key_constraints():
    with SessionLocal() as db:
        db.add_all([
            Company(company_name='Company One', business_registration_number='BRN-DUPLICATE', country='KR'),
            Company(company_name='Company Two', business_registration_number='BRN-DUPLICATE', country='US'),
        ])
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(MemberProfile(user_id=999999, member_type='SEARCH'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        user = db.query(User).filter(User.email == 'bob@example.com').one()
        db.add(CompanyMember(company_id=999999, user_id=user.id, trading_role='BUYER'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        company = Company(
            company_name='Constraint Metals',
            business_registration_number='BRN-UNIQUE',
            country='KR',
        )
        db.add(company)
        db.flush()
        db.add(CompanyMember(company_id=company.id, user_id=user.id, trading_role='BUYER'))
        db.commit()

        db.add(CompanyMember(company_id=company.id, user_id=user.id, trading_role='SELLER'))
        with pytest.raises(IntegrityError):
            db.commit()


def test_member_profile_requires_jwt_and_cannot_select_another_user(client):
    assert client.get('/members/me').status_code == 401

    buyer = login(client, 'bob@example.com')
    response = client.get(
        '/members/me',
        params={'user_id': 999},
        headers=auth_headers(buyer['access_token']),
    )
    assert response.status_code == 200
    assert response.json()['user_id'] == buyer['user_id']
    assert client.get('/members/999', headers=auth_headers(buyer['access_token'])).status_code == 404


def test_additive_table_creation_preserves_existing_user(tmp_path):
    migration_engine = create_engine(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    legacy_metadata = MetaData()
    legacy_users = Table(
        'users',
        legacy_metadata,
        Column('id', Integer, primary_key=True),
        Column('company_name', String(150), nullable=True),
        Column('name', String(100), nullable=False),
        Column('email', String(255), nullable=False, unique=True),
        Column('password', String(255), nullable=False),
        Column('role', String(50), nullable=False),
        Column('created_at', DateTime, nullable=False),
    )
    legacy_metadata.create_all(migration_engine)

    with migration_engine.begin() as connection:
        connection.execute(legacy_users.insert().values(
            id=8,
            company_name='Existing Co',
            name='Existing User',
            email='existing@example.com',
            password='unchanged',
            role='BUYER',
            created_at=datetime(2026, 1, 1),
        ))

    Base.metadata.create_all(migration_engine)

    table_names = set(inspect(migration_engine).get_table_names())
    assert {'member_profiles', 'companies', 'company_members', 'investor_profiles'} <= table_names
    with migration_engine.connect() as connection:
        preserved_user = connection.execute(select(legacy_users)).mappings().one()
    assert preserved_user['id'] == 8
    assert preserved_user['email'] == 'existing@example.com'
    assert preserved_user['password'] == 'unchanged'
    assert preserved_user['role'] == 'BUYER'