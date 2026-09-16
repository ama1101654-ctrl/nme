from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, event, func
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
