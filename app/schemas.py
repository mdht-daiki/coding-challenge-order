from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel


def _post(client, i):
    return client.post("/customers", json={"name": f"U{i}", "email": f"u{i}@ex.com"})


def test_many_parallel_posts(client):
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(_post, repeat(client), range(200)))
    assert all(r.status_code == 200 for r in results)


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

    model_config = ConfigDict(alias_generator=to_camel)
