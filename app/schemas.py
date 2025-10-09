from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictInt, field_validator
from pydantic.alias_generators import to_camel


def validate_name_trim_and_noempty(v: str) -> str:
    """共通のname検証 トリムして空文字を拒否する"""
    v2 = v.strip()
    if len(v2) == 0:
        raise ValueError("name must not be blank")
    return v2


class CustomerWithId(BaseModel):
    cust_id: str
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: str) -> str:
        return validate_name_trim_and_noempty(v)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: object) -> object:
        return v.lower() if isinstance(v, str) else v

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def name_trim_and_noempty(cls, v: str) -> str:
        return validate_name_trim_and_noempty(v)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit_price: StrictInt = Field(..., ge=1, le=1_000_000)

    @field_validator("name", mode="before")
    @classmethod
    def name_trim_and_noempty(cls, v: str) -> str:
        return validate_name_trim_and_noempty(v)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ProductWithId(BaseModel):
    prod_id: str = Field(min_length=1, max_length=100)
    name: str
    unit_price: int

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OrderItemCreate(BaseModel):
    prod_id: str = Field(min_length=1, max_length=100)
    qty: int = Field(ge=1, le=1000)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OrderCreate(BaseModel):
    cust_id: str = Field(min_length=1)
    items: List[OrderItemCreate] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OrderItemCreateResponse(BaseModel):
    line_no: int = Field(ge=1)
    prod_id: str = Field(min_length=1, max_length=100)
    qty: int = Field(ge=1, le=1000)
    unit_price: int = Field(ge=1, le=1_000_000)
    line_amount: int = Field(ge=0, le=1_000_000_000)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OrderCreateResponse(BaseModel):
    order_id: str = Field(min_length=1)
    order_date: date
    total_amount: int = Field(ge=0)
    items: List[OrderItemCreateResponse]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class OrderSummary(BaseModel):
    order_id: str
    order_date: date
    total_amount: int = Field(ge=0)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AuthContext(BaseModel):
    """認証済みユーザのコンテキスト情報"""

    api_key: str
    customer_id: Optional[str]  # Noneの場合は管理者
    is_admin: bool
