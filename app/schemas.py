from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel


class CustomerWithId(BaseModel):
    cust_id: str
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, v: str) -> str:
        return v.strip()

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
        v2 = v.strip()
        if len(v2) == 0:
            raise ValueError("name must not be blank")
        return v2

    model_config = ConfigDict(alias_generator=to_camel)
