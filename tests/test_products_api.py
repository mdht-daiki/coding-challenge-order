import re

import pytest

from tests.helpers import post_json


@pytest.mark.parametrize("name", [" ", "A" * 101])
def test_create_product_name_boundary(client, name):
    response = post_json(
        client, "/products", {"name": name, "unitPrice": 10000}, api_key="test-secret"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("price", [0, 1_000_001])
def test_create_product_price_boundary(client, price):
    response = post_json(
        client, "/products", {"name": "P", "unitPrice": price}, api_key="test-secret"
    )
    assert response.status_code == 400


def test_create_product_ok(client):
    response = post_json(
        client, "/products", {"name": "Pen", "unitPrice": 100}, api_key="test-secret"
    )
    assert response.status_code == 201
    assert "Location" in response.headers
    body = response.json()
    assert re.fullmatch(r"P_[0-9a-f]{8}", body["prodId"])
    assert body["name"] == "Pen"
    assert body["unitPrice"] == 100


def test_create_product_duplicate_name_case_insensitive(client):
    first_response = post_json(
        client,
        "/products",
        {"name": "Notebook", "unitPrice": 500},
        api_key="test-secret",
    )
    assert first_response.status_code == 201
    second_response = post_json(
        client,
        "/products",
        {"name": "notebook", "unitPrice": 800},
        api_key="test-secret",
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "NAME_DUP"
