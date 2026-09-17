from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event, func, text
from sqlalchemy.orm import relationship, validates

from .database import Base
from .password_security import PASSWORD_DISABLED_VALUE, hash_password


class Item(Base):
    """A simple item model for the MVP backend."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    """A simple user model for the trading platform."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False, default=PASSWORD_DISABLED_VALUE)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    member_profile = relationship("MemberProfile", back_populates="user", uselist=False)
    company_memberships = relationship("CompanyMember", back_populates="user")
    investor_profile = relationship("InvestorProfile", back_populates="user", uselist=False)


@event.listens_for(User, "before_insert")
def hash_new_user_password(_, __, user):
    """Ensure direct ORM user creation never persists a plaintext password."""
    if user.password_hash:
        user.password = PASSWORD_DISABLED_VALUE
        return
    if not user.password or user.password == PASSWORD_DISABLED_VALUE:
        raise ValueError("Password is required")
    user.password_hash = hash_password(user.password)
    user.password = PASSWORD_DISABLED_VALUE


class MemberProfile(Base):
    """NME business identity linked to an existing authentication user."""

    __tablename__ = "member_profiles"
    __table_args__ = (
        CheckConstraint("member_type IN ('COMPANY', 'INVESTOR', 'SEARCH')", name="ck_member_profiles_type"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_member_profiles_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    member_type = Column(String(20), nullable=False)
    display_name = Column(String(150), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="member_profile")


class Company(Base):
    """Minimal company identity for NME membership."""

    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_companies_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=False, index=True)
    business_registration_number = Column(String(50), unique=True, nullable=False, index=True)
    country = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    members = relationship("CompanyMember", back_populates="company")
    warehouses = relationship("Warehouse", back_populates="company")


class CompanyMember(Base):
    """A user's membership and trading role within a company."""

    __tablename__ = "company_members"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_members_company_user"),
        CheckConstraint("trading_role IN ('BUYER', 'SELLER', 'BOTH')", name="ck_company_members_trading_role"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_company_members_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trading_role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    company = relationship("Company", back_populates="members")
    user = relationship("User", back_populates="company_memberships")


class InvestorProfile(Base):
    """Minimal investor identity without financial account or investment data."""

    __tablename__ = "investor_profiles"
    __table_args__ = (
        CheckConstraint("investor_type IN ('INDIVIDUAL', 'CORPORATE')", name="ck_investor_profiles_type"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_investor_profiles_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    investor_type = Column(String(20), nullable=False)
    display_name = Column(String(150), nullable=True)
    country = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="investor_profile")


class MetalMaster(Base):
    """Canonical metal reference data independent of product listings."""

    __tablename__ = "metal_masters"
    __table_args__ = (
        UniqueConstraint("code", name="uq_metal_masters_code"),
        CheckConstraint("TRIM(code) <> ''", name="ck_metal_masters_code_not_blank"),
        CheckConstraint("code = UPPER(code)", name="ck_metal_masters_code_uppercase"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_metal_masters_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    grades = relationship("MetalGradeMaster", back_populates="metal")

    @validates("code")
    def normalize_code(self, _, value):
        normalized = str(value or "").strip().upper()
        if not normalized:
            raise ValueError("Metal code is required")
        return normalized


class MetalGradeMaster(Base):
    """Canonical grade reference data scoped to a metal master."""

    __tablename__ = "metal_grade_masters"
    __table_args__ = (
        UniqueConstraint("metal_id", "code", name="uq_metal_grade_masters_metal_code"),
        CheckConstraint("TRIM(code) <> ''", name="ck_metal_grade_masters_code_not_blank"),
        CheckConstraint("code = UPPER(code)", name="ck_metal_grade_masters_code_uppercase"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_metal_grade_masters_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    metal_id = Column(Integer, ForeignKey("metal_masters.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    metal = relationship("MetalMaster", back_populates="grades")

    @validates("code")
    def normalize_code(self, _, value):
        normalized = str(value or "").strip().upper()
        if not normalized:
            raise ValueError("Grade code is required")
        return normalized


class Warehouse(Base):
    """A company-owned physical storage location reference."""

    __tablename__ = "warehouses"
    __table_args__ = (
        UniqueConstraint("code", name="uq_warehouses_code"),
        CheckConstraint("TRIM(code) <> ''", name="ck_warehouses_code_not_blank"),
        CheckConstraint("code = UPPER(code)", name="ck_warehouses_code_uppercase"),
        CheckConstraint("TRIM(name) <> ''", name="ck_warehouses_name_not_blank"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_warehouses_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    company = relationship("Company", back_populates="warehouses")
    inventories = relationship("Inventory", back_populates="warehouse")

    @validates("code")
    def normalize_code(self, _, value):
        normalized = str(value or "").strip().upper()
        if not normalized:
            raise ValueError("Warehouse code is required")
        return normalized

    @validates("name")
    def validate_name(self, _, value):
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Warehouse name is required")
        return normalized


class Inventory(Base):
    """Future physical stock record kept independent from product listings."""

    __tablename__ = "inventories"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventories_quantity_nonnegative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_inventories_reserved_nonnegative"),
        CheckConstraint("reserved_quantity <= quantity", name="ck_inventories_reserved_within_quantity"),
        CheckConstraint("TRIM(unit) <> ''", name="ck_inventories_unit_not_blank"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_inventories_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    metal_id = Column(Integer, ForeignKey("metal_masters.id"), nullable=True, index=True)
    grade_id = Column(Integer, ForeignKey("metal_grade_masters.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    quantity = Column(Float, nullable=False)
    reserved_quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    warehouse = relationship("Warehouse", back_populates="inventories")
    metal = relationship("MetalMaster")
    grade = relationship("MetalGradeMaster")
    product = relationship("Product")

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity


class AuthSession(Base):
    """Persisted refresh session metadata for JWT rotation and revoke."""

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    refresh_jti = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Product(Base):
    """A simple product listing model for the trading platform."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, nullable=False, index=True)
    metal = Column(String(100), nullable=False)
    grade = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False)
    reserved_quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="available")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Order(Base):
    """A minimal Order model supporting both BUY and SELL side submissions."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    buyer_id = Column(Integer, nullable=True, index=True)
    seller_id = Column(Integer, nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    remaining_quantity = Column(Integer, nullable=True, default=None, index=True)
    price = Column(Integer, nullable=False)
    side = Column(String(10), nullable=False, default="buy", index=True)
    status = Column(String(50), nullable=False, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Trade(Base):
    """A minimal execution ledger for future matching work.

    The table intentionally records actual trade executions without changing the
    existing Deal negotiation workflow. This keeps current APIs and data intact
    while preparing for a later matching engine implementation.
    """

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    buy_order_id = Column(Integer, nullable=False, index=True)
    sell_order_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Contract(Base):
    """Immutable commercial terms captured from one matched trade."""

    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint("contract_no", name="uq_contracts_contract_no"),
        UniqueConstraint("trade_id", name="uq_contracts_trade_id"),
        CheckConstraint("TRIM(contract_no) <> ''", name="ck_contracts_no_not_blank"),
        CheckConstraint("quantity > 0", name="ck_contracts_quantity_positive"),
        CheckConstraint("TRIM(unit) <> ''", name="ck_contracts_unit_not_blank"),
        CheckConstraint("price > 0", name="ck_contracts_price_positive"),
        CheckConstraint("TRIM(currency) <> ''", name="ck_contracts_currency_not_blank"),
        CheckConstraint("total_value > 0", name="ck_contracts_total_value_positive"),
        CheckConstraint(
            "brand IS NULL OR (TRIM(brand) <> '' AND LENGTH(brand) <= 100)",
            name="ck_contracts_brand",
        ),
        CheckConstraint(
            "tolerance IS NULL OR (TRIM(tolerance) <> '' AND LENGTH(tolerance) <= 100)",
            name="ck_contracts_tolerance",
        ),
        CheckConstraint(
            "quotation_period IS NULL OR (TRIM(quotation_period) <> '' AND LENGTH(quotation_period) <= 200)",
            name="ck_contracts_quotation_period",
        ),
        CheckConstraint(
            "delivery_term IS NULL OR (TRIM(delivery_term) <> '' AND LENGTH(delivery_term) <= 100)",
            name="ck_contracts_delivery_term",
        ),
        CheckConstraint(
            "delivery_location IS NULL OR (TRIM(delivery_location) <> '' AND LENGTH(delivery_location) <= 200)",
            name="ck_contracts_delivery_location",
        ),
        CheckConstraint(
            "payment_term IS NULL OR (TRIM(payment_term) <> '' AND LENGTH(payment_term) <= 200)",
            name="ck_contracts_payment_term",
        ),
        CheckConstraint(
            "partial_delivery IS NULL OR partial_delivery IN ('YES', 'NO')",
            name="ck_contracts_partial_delivery",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="ck_contracts_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_no = Column(String(50), nullable=False, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), nullable=False)
    price = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="KRW")
    total_value = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="DRAFT")
    brand = Column(String(100), nullable=True)
    tolerance = Column(String(100), nullable=True)
    quotation_period = Column(String(200), nullable=True)
    delivery_term = Column(String(100), nullable=True)
    delivery_location = Column(String(200), nullable=True)
    payment_term = Column(String(200), nullable=True)
    partial_delivery = Column(String(3), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trade = relationship("Trade")
    product = relationship("Product")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
    revisions = relationship("ContractRevision", back_populates="contract", order_by="ContractRevision.revision_no")
    change_requests = relationship("ContractChangeRequest", back_populates="contract", order_by="ContractChangeRequest.id")


class ContractRevision(Base):
    """Immutable point-in-time snapshot of a Contract."""

    __tablename__ = "contract_revisions"
    __table_args__ = (
        UniqueConstraint("contract_id", "revision_no", name="uq_contract_revisions_contract_no"),
        CheckConstraint("revision_no > 0", name="ck_contract_revisions_no_positive"),
        CheckConstraint(
            "revision_status IN ('DRAFT', 'ACTIVE', 'SUPERSEDED')",
            name="ck_contract_revisions_status",
        ),
        CheckConstraint("TRIM(contract_no) <> ''", name="ck_contract_revisions_contract_no_not_blank"),
        CheckConstraint("quantity > 0", name="ck_contract_revisions_quantity_positive"),
        CheckConstraint("TRIM(unit) <> ''", name="ck_contract_revisions_unit_not_blank"),
        CheckConstraint("price > 0", name="ck_contract_revisions_price_positive"),
        CheckConstraint("TRIM(currency) <> ''", name="ck_contract_revisions_currency_not_blank"),
        CheckConstraint("total_value > 0", name="ck_contract_revisions_total_value_positive"),
        CheckConstraint("brand IS NULL OR (TRIM(brand) <> '' AND LENGTH(brand) <= 100)", name="ck_contract_revisions_brand"),
        CheckConstraint("tolerance IS NULL OR (TRIM(tolerance) <> '' AND LENGTH(tolerance) <= 100)", name="ck_contract_revisions_tolerance"),
        CheckConstraint("quotation_period IS NULL OR (TRIM(quotation_period) <> '' AND LENGTH(quotation_period) <= 200)", name="ck_contract_revisions_quotation_period"),
        CheckConstraint("delivery_term IS NULL OR (TRIM(delivery_term) <> '' AND LENGTH(delivery_term) <= 100)", name="ck_contract_revisions_delivery_term"),
        CheckConstraint("delivery_location IS NULL OR (TRIM(delivery_location) <> '' AND LENGTH(delivery_location) <= 200)", name="ck_contract_revisions_delivery_location"),
        CheckConstraint("payment_term IS NULL OR (TRIM(payment_term) <> '' AND LENGTH(payment_term) <= 200)", name="ck_contract_revisions_payment_term"),
        CheckConstraint("partial_delivery IS NULL OR partial_delivery IN ('YES', 'NO')", name="ck_contract_revisions_partial_delivery"),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="ck_contract_revisions_contract_status",
        ),
    )

    revision_id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    revision_no = Column(Integer, nullable=False)
    revision_status = Column(String(20), nullable=False, default="DRAFT")
    contract_no = Column(String(50), nullable=False)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(20), nullable=False)
    price = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    total_value = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    brand = Column(String(100), nullable=True)
    tolerance = Column(String(100), nullable=True)
    quotation_period = Column(String(200), nullable=True)
    delivery_term = Column(String(100), nullable=True)
    delivery_location = Column(String(200), nullable=True)
    payment_term = Column(String(200), nullable=True)
    partial_delivery = Column(String(3), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contract = relationship("Contract", back_populates="revisions")


class ContractChangeRequest(Base):
    """Approval-pending request linking an immutable base and proposed revision."""

    __tablename__ = "contract_change_requests"
    __table_args__ = (
        CheckConstraint("TRIM(reason) <> ''", name="ck_contract_change_requests_reason_not_blank"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="ck_contract_change_requests_status",
        ),
        CheckConstraint(
            "base_revision_id <> proposed_revision_id",
            name="ck_contract_change_requests_distinct_revisions",
        ),
        Index(
            "uq_contract_change_requests_pending_contract",
            "contract_id",
            unique=True,
            sqlite_where=text("status = 'PENDING'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    base_revision_id = Column(Integer, ForeignKey("contract_revisions.revision_id"), nullable=False, index=True)
    proposed_revision_id = Column(Integer, ForeignKey("contract_revisions.revision_id"), nullable=False, unique=True, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    contract = relationship("Contract", back_populates="change_requests")
    base_revision = relationship("ContractRevision", foreign_keys=[base_revision_id])
    proposed_revision = relationship("ContractRevision", foreign_keys=[proposed_revision_id])
    requested_by_user = relationship("User", foreign_keys=[requested_by_user_id])

    @property
    def base_revision_no(self):
        return self.base_revision.revision_no

    @property
    def proposed_revision_no(self):
        return self.proposed_revision.revision_no

    @property
    def proposed_revision_status(self):
        return self.proposed_revision.revision_status


class Deal(Base):
    """A minimal Deal model representing a negotiation proposal from a buyer."""

    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    buyer_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    proposed_price = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="NEGOTIATING")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
