from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
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

    model_config = ConfigDict(alias_generator=to_camel)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    unit_price: int = Field(..., ge=1, le=1_000_000)

    @field_validator("name", mode="before")
    @classmethod
    def name_trim_and_noempty(cls, v: str) -> str:
        return validate_name_trim_and_noempty(v)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ProductWithId(BaseModel):
    prod_id: str
    name: str
    unit_price: int

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: str) -> str:
        return validate_name_trim_and_noempty(v)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
