from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class CompanyMembershipResponse(BaseModel):
    company_id: int
    company_name: str
    trading_role: Literal["BUYER", "SELLER", "BOTH"]
    status: Literal["ACTIVE", "INACTIVE"]


class InvestorProfileSummary(BaseModel):
    investor_type: Literal["INDIVIDUAL", "CORPORATE"]
    display_name: str | None = None
    country: str | None = None
    status: Literal["ACTIVE", "INACTIVE"]


class MemberMeResponse(BaseModel):
    user_id: int
    member_type: Literal["COMPANY", "INVESTOR", "SEARCH"] | None = None
    display_name: str | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None
    companies: list[CompanyMembershipResponse] = Field(default_factory=list)
    investor_profile: InvestorProfileSummary | None = None


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
    reserved_quantity: float | None = 0.0
    unit: str
    price: int
    status: str = "available"


class ProductResponse(ProductCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetalMasterResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    status: Literal["ACTIVE", "INACTIVE"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetalGradeMasterResponse(BaseModel):
    id: int
    metal_id: int
    code: str
    name: str
    description: str | None = None
    status: Literal["ACTIVE", "INACTIVE"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseResponse(BaseModel):
    id: int
    company_id: int
    code: str
    name: str
    country: str | None = None
    region: str | None = None
    address: str | None = None
    status: Literal["ACTIVE", "INACTIVE"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryResponse(BaseModel):
    id: int
    warehouse_id: int
    metal_id: int | None = None
    grade_id: int | None = None
    product_id: int | None = None
    quantity: float
    reserved_quantity: float
    available_quantity: float
    unit: str
    status: Literal["ACTIVE", "INACTIVE"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Schema used when creating a new Order.

    BUY orders are the legacy format; SELL orders are added as an additive
    side-specific flow that keeps the existing API compatible.
    """

    product_id: int
    buyer_id: int | None = None
    seller_id: int | None = None
    quantity: int
    price: int
    side: str = "buy"

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value):
        if value is None:
            return "buy"
        normalized = str(value).strip().lower()
        if normalized not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        return normalized


class OrderResponse(BaseModel):
    id: int
    product_id: int
    buyer_id: int | None = None
    seller_id: int | None = None
    quantity: int
    remaining_quantity: int | None = None
    price: int
    side: str = "buy"
    status: str
    created_at: datetime

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value):
        if value is None:
            return "buy"
        normalized = str(value).strip().lower()
        if normalized not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        return normalized

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    """Schema for updating an order's status. Only allowed literals accepted."""

    status: Literal[
        "PENDING",
        "PARTIAL",
        "FILLED",
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


class OrderBookLevel(BaseModel):
    price: float
    quantity: float

    model_config = ConfigDict(from_attributes=True)


class OrderBookResponse(BaseModel):
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    time: str

    model_config = ConfigDict(from_attributes=True)


class TradeHistoryEntry(BaseModel):
    trade_id: int
    product_id: int
    buy_order_id: int
    sell_order_id: int
    quantity: int
    price: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    trade_id: int
    product_id: int
    price: float
    quantity: float
    side: Literal["buy", "sell"]
    time: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketSummaryResponse(BaseModel):
    product_id: int
    trade_count: int
    total_quantity: float
    total_value: float
    latest_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    latest_trade_time: datetime | None = None
    average_price: float | None = None

    model_config = ConfigDict(from_attributes=True)
