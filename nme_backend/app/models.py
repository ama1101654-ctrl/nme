from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from .database import Base


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
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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
    unit = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default="available")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Order(Base):
    """A minimal Order model representing a buyer's request for a product."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    buyer_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
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
