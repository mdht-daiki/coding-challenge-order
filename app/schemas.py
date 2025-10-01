from pydantic import BaseModel, EmailStr, Field


class CustomerWithId(BaseModel):
    custId: str
    name: str
    email: EmailStr


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
