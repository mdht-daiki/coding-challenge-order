from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_settings import SettingsConfigDict


class CustomerWithId(BaseModel):
    cust_id: str
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def trim_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()

    model_config = SettingsConfigDict(validate_by_name=True, validate_by_alias=True)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
