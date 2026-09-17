from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_

from sqlalchemy.orm import Session, joinedload

from .models import AuthSession, Company, CompanyMember, Contract, ContractChangeRequest, ContractChangeRequestApproval, ContractExecution, ContractRevision, Deal, Inventory, InvestorProfile, Item, MemberProfile, MetalGradeMaster, MetalMaster, Order, Product, Trade, User, Warehouse
from .password_security import verify_password
from .schemas import ItemCreate, ProductCreate, UserCreate, OrderCreate, DealCreate


def create_item(db: Session, item: ItemCreate) -> Item:
    """Create a new item and save it to the database."""
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_items(db: Session, skip: int = 0, limit: int = 100):
    """Return items ordered by most recent first."""
    return db.query(Item).order_by(Item.id.desc()).offset(skip).limit(limit).all()


def create_product(db: Session, product: ProductCreate) -> Product:
    """Create a new product listing and save it to the database."""
    db_product = Product(
        seller_id=product.seller_id,
        metal=product.metal,
        grade=product.grade,
        quantity=product.quantity,
        reserved_quantity=0.0 if product.reserved_quantity is None else float(product.reserved_quantity),
        unit=product.unit,
        price=product.price,
        status=product.status,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_products(db: Session, skip: int = 0, limit: int = 100):
    """Return products ordered by most recent first."""
    return db.query(Product).order_by(Product.id.desc()).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int):
    """Return a product by id."""
    return db.query(Product).filter(Product.id == product_id).first()


def get_metal_masters(db: Session):
    """Return all metal masters, including inactive historical values."""
    return db.query(MetalMaster).order_by(MetalMaster.code.asc()).all()


def get_metal_master(db: Session, metal_id: int):
    """Return a metal master by id."""
    return db.query(MetalMaster).filter(MetalMaster.id == metal_id).first()


def get_grades_by_metal(db: Session, metal_id: int):
    """Return all grade masters for one metal, including inactive values."""
    return (
        db.query(MetalGradeMaster)
        .filter(MetalGradeMaster.metal_id == metal_id)
        .order_by(MetalGradeMaster.code.asc())
        .all()
    )


def get_grade_master(db: Session, grade_id: int):
    """Return a grade master by id."""
    return db.query(MetalGradeMaster).filter(MetalGradeMaster.id == grade_id).first()


def get_warehouses(db: Session):
    """Return all warehouses, including inactive historical locations."""
    return db.query(Warehouse).order_by(Warehouse.code.asc()).all()


def get_warehouse(db: Session, warehouse_id: int):
    """Return a warehouse by id."""
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def get_company_warehouses(db: Session, company_id: int):
    """Return all warehouses owned by one company."""
    return (
        db.query(Warehouse)
        .filter(Warehouse.company_id == company_id)
        .order_by(Warehouse.code.asc())
        .all()
    )


def get_company(db: Session, company_id: int):
    """Return a company by id."""
    return db.query(Company).filter(Company.id == company_id).first()


def get_inventories(db: Session):
    """Return all physical inventory references without mutating listings."""
    return db.query(Inventory).order_by(Inventory.id.asc()).all()


def get_inventory(db: Session, inventory_id: int):
    """Return an inventory record by id."""
    return db.query(Inventory).filter(Inventory.id == inventory_id).first()


def get_contract(db: Session, contract_id: int):
    """Return a contract by id."""
    return db.query(Contract).filter(Contract.id == contract_id).first()


def get_contract_by_trade(db: Session, trade_id: int):
    """Return the single contract for a trade, if present."""
    return db.query(Contract).filter(Contract.trade_id == trade_id).first()


def get_contracts_for_user(db: Session, user: User):
    """Return all contracts for admins or participant contracts for other users."""
    query = db.query(Contract)
    if str(user.role or "").upper() != "ADMIN":
        query = query.filter(or_(Contract.buyer_id == user.id, Contract.seller_id == user.id))
    return query.order_by(Contract.id.desc()).all()


def create_contract_from_trade(db: Session, trade_id: int):
    """Validate a trade graph and stage an immutable contract snapshot."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if trade is None:
        return None

    buy_order = db.query(Order).filter(Order.id == trade.buy_order_id).first()
    sell_order = db.query(Order).filter(Order.id == trade.sell_order_id).first()
    product = db.query(Product).filter(Product.id == trade.product_id).first()
    if buy_order is None or sell_order is None or product is None:
        raise ValueError("Trade references are incomplete")
    if buy_order.side != "buy" or sell_order.side != "sell":
        raise ValueError("Trade order sides are inconsistent")
    if trade.product_id != buy_order.product_id or trade.product_id != sell_order.product_id:
        raise ValueError("Trade and order products are inconsistent")
    if buy_order.buyer_id is None or sell_order.seller_id is None:
        raise ValueError("Trade participants are incomplete")
    if db.query(User).filter(User.id == buy_order.buyer_id).first() is None:
        raise ValueError("Trade buyer does not exist")
    if db.query(User).filter(User.id == sell_order.seller_id).first() is None:
        raise ValueError("Trade seller does not exist")
    if trade.quantity is None or trade.quantity <= 0 or trade.price is None or trade.price <= 0:
        raise ValueError("Trade quantity and price must be positive")
    if not str(product.unit or "").strip():
        raise ValueError("Product unit is required")

    trade_year = trade.created_at.year if trade.created_at is not None else datetime.now(timezone.utc).year
    contract = Contract(
        contract_no=f"NME-CT-{trade_year}-{trade.id:010d}",
        trade_id=trade.id,
        product_id=trade.product_id,
        buyer_id=buy_order.buyer_id,
        seller_id=sell_order.seller_id,
        quantity=trade.quantity,
        unit=str(product.unit).strip().upper(),
        price=trade.price,
        currency="KRW",
        total_value=trade.quantity * trade.price,
        status="DRAFT",
    )
    db.add(contract)
    db.flush()
    return contract


def get_contract_revisions(db: Session, contract_id: int):
    """Return immutable snapshots for one Contract in revision order."""
    return (
        db.query(ContractRevision)
        .filter(ContractRevision.contract_id == contract_id)
        .order_by(ContractRevision.revision_no.asc())
        .all()
    )


def get_contract_revision(db: Session, contract_id: int, revision_id: int):
    """Return one immutable snapshot scoped to its Contract."""
    return (
        db.query(ContractRevision)
        .filter(
            ContractRevision.contract_id == contract_id,
            ContractRevision.revision_id == revision_id,
        )
        .first()
    )


def create_contract_revision(db: Session, contract: Contract):
    """Stage the next immutable snapshot using only server-owned Contract data."""
    current_revision_no = (
        db.query(func.max(ContractRevision.revision_no))
        .filter(ContractRevision.contract_id == contract.id)
        .scalar()
    )
    revision = ContractRevision(
        contract_id=contract.id,
        revision_no=(current_revision_no or 0) + 1,
        revision_status="DRAFT",
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
    db.flush()
    return revision


def get_latest_contract_revision(db: Session, contract_id: int):
    """Return the latest immutable revision for one Contract."""
    return (
        db.query(ContractRevision)
        .filter(ContractRevision.contract_id == contract_id)
        .order_by(ContractRevision.revision_no.desc())
        .first()
    )


def get_pending_contract_change_request(db: Session, contract_id: int):
    """Return the single approval-pending request for a Contract, if present."""
    return (
        db.query(ContractChangeRequest)
        .filter(
            ContractChangeRequest.contract_id == contract_id,
            ContractChangeRequest.status == "PENDING",
        )
        .first()
    )


def get_contract_change_requests(db: Session, contract_id: int):
    """Return Change Requests newest first without mutating their revisions."""
    return (
        db.query(ContractChangeRequest)
        .filter(ContractChangeRequest.contract_id == contract_id)
        .order_by(ContractChangeRequest.id.desc())
        .all()
    )


def get_contract_change_request(db: Session, contract_id: int, change_request_id: int):
    """Return one Change Request scoped to its Contract."""
    return (
        db.query(ContractChangeRequest)
        .filter(
            ContractChangeRequest.contract_id == contract_id,
            ContractChangeRequest.id == change_request_id,
        )
        .first()
    )


def create_contract_change_request(
    db: Session,
    contract: Contract,
    base_revision: ContractRevision,
    requested_by_user_id: int,
    reason: str,
    term_changes: dict,
):
    """Stage a proposed DRAFT revision and its PENDING request atomically."""
    current_revision_no = (
        db.query(func.max(ContractRevision.revision_no))
        .filter(ContractRevision.contract_id == contract.id)
        .scalar()
    )
    snapshot = {
        "contract_no": base_revision.contract_no,
        "trade_id": base_revision.trade_id,
        "product_id": base_revision.product_id,
        "buyer_id": base_revision.buyer_id,
        "seller_id": base_revision.seller_id,
        "quantity": base_revision.quantity,
        "unit": base_revision.unit,
        "price": base_revision.price,
        "currency": base_revision.currency,
        "total_value": base_revision.total_value,
        "status": base_revision.status,
        "brand": base_revision.brand,
        "tolerance": base_revision.tolerance,
        "quotation_period": base_revision.quotation_period,
        "delivery_term": base_revision.delivery_term,
        "delivery_location": base_revision.delivery_location,
        "payment_term": base_revision.payment_term,
        "partial_delivery": base_revision.partial_delivery,
    }
    snapshot.update(term_changes)
    proposed_revision = ContractRevision(
        contract_id=contract.id,
        revision_no=(current_revision_no or 0) + 1,
        revision_status="DRAFT",
        **snapshot,
    )
    db.add(proposed_revision)
    db.flush()
    change_request = ContractChangeRequest(
        contract_id=contract.id,
        base_revision_id=base_revision.revision_id,
        proposed_revision_id=proposed_revision.revision_id,
        requested_by_user_id=requested_by_user_id,
        reason=reason,
        status="PENDING",
    )
    db.add(change_request)
    db.flush()
    return change_request


def get_contract_change_request_approval(db: Session, change_request_id: int, approver_side: str):
    """Return an immutable decision already recorded for one party side."""
    return (
        db.query(ContractChangeRequestApproval)
        .filter(
            ContractChangeRequestApproval.change_request_id == change_request_id,
            ContractChangeRequestApproval.approver_side == approver_side,
        )
        .first()
    )


def stage_contract_change_request_approval(
    db: Session,
    change_request: ContractChangeRequest,
    approver_user_id: int,
    approver_side: str,
):
    """Stage one approval and finalize revisions only after both sides approve."""
    approval = ContractChangeRequestApproval(
        change_request_id=change_request.id,
        approver_user_id=approver_user_id,
        approver_side=approver_side,
        decision="APPROVED",
    )
    db.add(approval)
    db.flush()

    approved_sides = {
        row.approver_side
        for row in db.query(ContractChangeRequestApproval)
        .filter(
            ContractChangeRequestApproval.change_request_id == change_request.id,
            ContractChangeRequestApproval.decision == "APPROVED",
        )
        .all()
    }
    if approved_sides == {"BUYER", "SELLER"}:
        base_revision = change_request.base_revision
        proposed_revision = change_request.proposed_revision
        if base_revision.revision_status != "ACTIVE" or proposed_revision.revision_status != "DRAFT":
            raise ValueError("Change request revisions are not eligible for approval")
        base_revision.revision_status = "SUPERSEDED"
        proposed_revision.revision_status = "ACTIVE"
        change_request.status = "APPROVED"
        db.flush()
    return change_request


def stage_contract_change_request_rejection(
    db: Session,
    change_request: ContractChangeRequest,
    approver_user_id: int,
    approver_side: str,
    reason: str,
):
    """Stage one immutable rejection while leaving both revisions unchanged."""
    rejection = ContractChangeRequestApproval(
        change_request_id=change_request.id,
        approver_user_id=approver_user_id,
        approver_side=approver_side,
        decision="REJECTED",
        comment=reason,
    )
    db.add(rejection)
    change_request.status = "REJECTED"
    db.flush()
    return change_request


def get_contract_execution(db: Session, contract_id: int):
    """Return the single execution fixed to one Contract Revision, if present."""
    return (
        db.query(ContractExecution)
        .filter(ContractExecution.contract_id == contract_id)
        .first()
    )


def get_active_contract_revision(db: Session, contract_id: int):
    """Return the Contract's sole ACTIVE Revision."""
    return (
        db.query(ContractRevision)
        .filter(
            ContractRevision.contract_id == contract_id,
            ContractRevision.revision_status == "ACTIVE",
        )
        .first()
    )


def active_revision_is_execution_eligible(db: Session, contract_id: int, revision_id: int):
    """Allow an initial ACTIVE Revision or an approved proposal Revision."""
    change_requests = (
        db.query(ContractChangeRequest)
        .filter(ContractChangeRequest.contract_id == contract_id)
        .all()
    )
    if not change_requests:
        return True
    return any(
        request.proposed_revision_id == revision_id and request.status == "APPROVED"
        for request in change_requests
    )


def create_contract_execution(db: Session, contract_id: int, contract_revision_id: int):
    """Stage a READY execution without mutating its Contract or Revision."""
    execution = ContractExecution(
        contract_id=contract_id,
        contract_revision_id=contract_revision_id,
        status="READY",
    )
    db.add(execution)
    db.flush()
    return execution


def get_warehouse_inventory(db: Session, warehouse_id: int):
    """Return all inventory records held at one warehouse."""
    return (
        db.query(Inventory)
        .filter(Inventory.warehouse_id == warehouse_id)
        .order_by(Inventory.id.asc())
        .all()
    )


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user and save it to the database."""
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise ValueError("Email already registered")

    db_user = User(
        company_name=user.company_name,
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Return users ordered by most recent first."""
    return db.query(User).order_by(User.id.desc()).offset(skip).limit(limit).all()


def get_user(db: Session, user_id: int):
    """Return a user by id."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    """Return a user by email."""
    return db.query(User).filter(User.email == email).first()


def get_member_profile_by_user(db: Session, user_id: int):
    """Return the optional NME business profile for an authentication user."""
    return db.query(MemberProfile).filter(MemberProfile.user_id == user_id).first()


def get_company_memberships_by_user(db: Session, user_id: int):
    """Return active and inactive company memberships with company identity."""
    return (
        db.query(CompanyMember)
        .options(joinedload(CompanyMember.company))
        .filter(CompanyMember.user_id == user_id)
        .order_by(CompanyMember.id.asc())
        .all()
    )


def get_investor_profile_by_user(db: Session, user_id: int):
    """Return the optional investor identity for an authentication user."""
    return db.query(InvestorProfile).filter(InvestorProfile.user_id == user_id).first()


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user using only the stored password hash."""
    user = get_user_by_email(db=db, email=email)
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_auth_session(db: Session, user_id: int, refresh_jti: str, expires_at: datetime) -> AuthSession:
    """Create a persisted auth session for a refresh token."""
    now_utc = datetime.now(timezone.utc)
    db_session = AuthSession(
        user_id=user_id,
        refresh_jti=refresh_jti,
        expires_at=expires_at,
        last_used_at=now_utc,
        revoked_at=None,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_auth_session_by_refresh_jti(db: Session, refresh_jti: str):
    """Return an auth session by refresh token jti."""
    return db.query(AuthSession).filter(AuthSession.refresh_jti == refresh_jti).first()


def get_auth_session_by_jti(db: Session, refresh_jti: str):
    """Backward-compatible alias for existing callers."""
    return get_auth_session_by_refresh_jti(db=db, refresh_jti=refresh_jti)


def get_active_auth_sessions_by_user(db: Session, user_id: int):
    """Return active (not revoked, not expired) auth sessions for a user."""
    now_utc = datetime.now(timezone.utc)
    return (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id)
        .filter(AuthSession.revoked_at.is_(None))
        .filter(AuthSession.expires_at > now_utc)
        .order_by(AuthSession.created_at.desc(), AuthSession.id.desc())
        .all()
    )


def get_auth_session_by_id_for_user(db: Session, session_id: int, user_id: int):
    """Return a session only when it belongs to the provided user."""
    return (
        db.query(AuthSession)
        .filter(AuthSession.id == session_id, AuthSession.user_id == user_id)
        .first()
    )


def touch_auth_session_last_used_at(db: Session, auth_session: AuthSession):
    """Update last_used_at for a successfully used refresh session."""
    auth_session.last_used_at = datetime.now(timezone.utc)
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    return auth_session


def revoke_auth_session(db: Session, auth_session: AuthSession):
    """Mark a specific auth session revoked if needed and return it."""
    if auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.now(timezone.utc)
        db.add(auth_session)
        db.commit()
        db.refresh(auth_session)

    return auth_session


def revoke_all_auth_sessions_for_user(db: Session, user_id: int):
    """Revoke all active auth sessions for a user and return revoke count."""
    sessions = get_active_auth_sessions_by_user(db=db, user_id=user_id)
    if not sessions:
        return 0

    now_utc = datetime.now(timezone.utc)
    for session in sessions:
        session.revoked_at = now_utc
        db.add(session)

    db.commit()
    return len(sessions)


def revoke_auth_session_by_jti(db: Session, refresh_jti: str):
    """Mark an auth session revoked if it exists."""
    auth_session = get_auth_session_by_refresh_jti(db=db, refresh_jti=refresh_jti)
    if auth_session is None:
        return None

    return revoke_auth_session(db=db, auth_session=auth_session)


def get_expired_auth_sessions(db: Session, retention_days: int):
    """Return expired sessions older than the retention cutoff."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    return (
        db.query(AuthSession)
        .filter(AuthSession.expires_at <= cutoff)
        .order_by(AuthSession.id.asc())
        .all()
    )


def get_revoked_auth_sessions(db: Session, retention_days: int):
    """Return revoked sessions older than the retention cutoff."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    return (
        db.query(AuthSession)
        .filter(AuthSession.revoked_at.is_not(None))
        .filter(AuthSession.revoked_at <= cutoff)
        .order_by(AuthSession.id.asc())
        .all()
    )


def cleanup_auth_sessions(db: Session, retention_days: int):
    """Delete expired/revoked sessions older than the retention cutoff.

    Active sessions are never deleted because they are neither expired nor
    revoked before the cutoff.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    deleted_count = (
        db.query(AuthSession)
        .filter(
            or_(
                AuthSession.expires_at <= cutoff,
                (AuthSession.revoked_at.is_not(None) & (AuthSession.revoked_at <= cutoff)),
            )
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted_count


def create_order(db: Session, order: OrderCreate) -> Order:
    """Create a new order and save it to the database."""
    db_order = Order(
        product_id=order.product_id,
        buyer_id=getattr(order, 'buyer_id', None),
        seller_id=getattr(order, 'seller_id', None),
        quantity=order.quantity,
        remaining_quantity=getattr(order, 'remaining_quantity', order.quantity),
        price=order.price,
        side=getattr(order, 'side', 'buy'),
        status="PENDING",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_orders(db: Session, skip: int = 0, limit: int = 100):
    """Return orders ordered by most recent first."""
    return db.query(Order).order_by(Order.id.desc()).offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int):
    """Return an order by id."""
    return db.query(Order).filter(Order.id == order_id).first()


def update_order_status(db: Session, order_id: int, new_status: str):
    """Update the status of an order following allowed transitions.

    Returns the updated Order, or None if not found. Raises ValueError on invalid transition.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        return None

    # Define allowed transitions while preserving the project's legacy status naming.
    allowed = {
        "PENDING": ["PARTIAL", "FILLED", "ACCEPTED", "CANCELLED"],
        "PARTIAL": ["PARTIAL", "FILLED", "CANCELLED"],
        "FILLED": [],
        "ACCEPTED": ["PAID", "CANCELLED"],
        "PAID": ["SHIPPED"],
        "SHIPPED": ["COMPLETED"],
        "COMPLETED": [],
        "CANCELLED": [],
    }

    current = order.status
    # Normalize None or unexpected current status
    if current not in allowed:
        raise ValueError(f"Invalid current order status: {current}")

    if new_status == current:
        # No change; treat as successful no-op
        return order

    if new_status not in allowed[current]:
        raise ValueError(f"Invalid order status transition: {current} -> {new_status}")

    # Apply change
    order.status = new_status
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_market_products(db: Session, skip: int = 0, limit: int = 100):
    """Return products that are currently available on the market.

    This function filters by the `status` field using the project's existing
    value for available products (currently "available").
    """
    return (
        db.query(Product)
        .filter(Product.status == "available")
        .order_by(Product.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_deal(db: Session, deal: DealCreate) -> Deal:
    """Create a new deal (negotiation) and save it to the database."""
    db_deal = Deal(
        product_id=deal.product_id,
        buyer_id=deal.buyer_id,
        quantity=deal.quantity,
        proposed_price=deal.proposed_price,
        status="NEGOTIATING",
    )
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


def get_deals(db: Session, skip: int = 0, limit: int = 100):
    """Return deals ordered by most recent first."""
    return db.query(Deal).order_by(Deal.id.desc()).offset(skip).limit(limit).all()


def get_deal(db: Session, deal_id: int):
    """Return a deal by id."""
    return db.query(Deal).filter(Deal.id == deal_id).first()


def update_deal_status(db: Session, deal_id: int, new_status: str):
    """Update the status of a deal following allowed transitions.

    Returns the updated Deal, or None if not found. Raises ValueError on invalid transition.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    allowed = {
        "NEGOTIATING": ["AGREED", "REJECTED", "CANCELLED"],
        "AGREED": [],
        "REJECTED": [],
        "CANCELLED": [],
    }

    current = deal.status
    if current not in allowed:
        raise ValueError(f"Invalid current deal status: {current}")

    if new_status == current:
        return deal

    if new_status not in allowed[current]:
        raise ValueError(f"Invalid deal status transition: {current} -> {new_status}")

    deal.status = new_status
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


def create_order_from_deal(db: Session, deal_id: int):
    """Create an Order from an AGREED Deal.

    Returns the created Order, or:
      - None if deal not found
      - raises ValueError if deal not in AGREED or order already exists
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    # Deal must be AGREED
    if deal.status != "AGREED":
        raise ValueError("Deal must be AGREED to create an order")

    # Prevent duplicate: check existing order with same deal fields
    existing = (
        db.query(Order)
        .filter(
            Order.product_id == deal.product_id,
            Order.buyer_id == deal.buyer_id,
            Order.quantity == deal.quantity,
            Order.price == deal.proposed_price,
        )
        .first()
    )
    if existing:
        raise ValueError("Order already created for this Deal")

    # Create order using existing pattern
    db_order = Order(
        product_id=deal.product_id,
        buyer_id=deal.buyer_id,
        seller_id=None,
        quantity=deal.quantity,
        remaining_quantity=deal.quantity,
        price=deal.proposed_price,
        side="buy",
        status="PENDING",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order_for_deal(db: Session, deal_id: int):
    """Return the Order that was created from a given Deal.

    Because Orders are not tied by foreign key to Deals in this simple schema,
    we match on the key fields used when the Order was created from the Deal.
    Returns the Order or None if not found; returns None if Deal does not exist.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    order = (
        db.query(Order)
        .filter(
            Order.product_id == deal.product_id,
            Order.buyer_id == deal.buyer_id,
            Order.quantity == deal.quantity,
            Order.price == deal.proposed_price,
        )
        .order_by(Order.id.desc())
        .first()
    )
    return order


def get_deal_completion(db: Session, deal_id: int):
    """Return a small dict describing the completion status for a Deal's Order.

    Returns None if Deal or Order not found; otherwise returns a dict with
    deal_id, order_id, status, completed (bool).
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        return None

    order = get_order_for_deal(db=db, deal_id=deal_id)
    if order is None:
        return None

    completed = (getattr(order, "status", None) == "COMPLETED")
    return {"deal_id": deal.id, "order_id": order.id, "status": order.status, "completed": completed}
