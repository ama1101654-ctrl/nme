from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    name: str
    description: str | None = None


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    company_name: str | None = None
    name: str
    email: str
    password: str
    role: str = "user"


class UserCreate(UserBase):
    pass


class UserResponse(BaseModel):
    id: int
    company_name: str | None = None
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

    model_config = ConfigDict(from_attributes=True)


class AuthSessionResponse(BaseModel):
    id: int
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    is_current: bool

    model_config = ConfigDict(from_attributes=True)


class AuthSessionActionResponse(BaseModel):
    status: str

    model_config = ConfigDict(from_attributes=True)


class AuthSessionCleanupResponse(BaseModel):
    status: str
    deleted_count: int
    retention_days: int

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    seller_id: int
    metal: str
    grade: str
    quantity: int
    unit: str
    price: int
    status: str = "available"


class ProductResponse(ProductCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Schema used when creating a new Order."""

    product_id: int
    buyer_id: int
    quantity: int
    price: int


class OrderResponse(BaseModel):
    id: int
    product_id: int
    buyer_id: int
    quantity: int
    price: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    """Schema for updating an order's status. Only allowed literals accepted."""

    status: Literal[
        "PENDING",
        "ACCEPTED",
        "PAID",
        "SHIPPED",
        "COMPLETED",
        "CANCELLED",
    ]


class MarketResponse(BaseModel):
    """Schema returned by GET /market representing a product available on the market."""

    product_id: int
    metal: str
    grade: str
    quantity: float
    unit: str
    price: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class DealCreate(BaseModel):
    product_id: int
    buyer_id: int
    quantity: int
    proposed_price: int


class DealResponse(BaseModel):
    id: int
    product_id: int
    buyer_id: int
    quantity: int
    proposed_price: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealStatusUpdate(BaseModel):
    status: Literal[
        "NEGOTIATING",
        "AGREED",
        "REJECTED",
        "CANCELLED",
    ]


class DealCompletionResponse(BaseModel):
    deal_id: int
    order_id: int
    status: str
    completed: bool

    model_config = ConfigDict(from_attributes=True)
