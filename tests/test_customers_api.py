import re

import pytest

from tests.helpers import post_json


@pytest.mark.parametrize("name", [" ", "A" * 101])
def test_create_customer_name_boundary(client, name):
    response = post_json(
        client,
        "/customers",
        {"name": name, "email": "b@example.com"},
        api_key="test-secret",
    )
    assert response.status_code == 400


def test_create_customer_ok(client):
    response = post_json(
        client,
        "/customers",
        {"name": "Alice", "email": "a@example.com"},
        api_key="test-secret",
    )
    assert response.status_code == 201
    assert "Location" in response.headers
    body = response.json()
    assert re.fullmatch(r"C_[0-9a-f]{8}", body["custId"])
    assert body["name"] == "Alice"
    assert body["email"] == "a@example.com"


def test_create_customer_duplicate_email(client):
    first_response = post_json(
        client,
        "/customers",
        {"name": "Bob", "email": "duplicate@example.com"},
        api_key="test-secret",
    )
    assert first_response.status_code == 201
    assert "Location" in first_response.headers
    second_response = post_json(
        client,
        "/customers",
        {"name": "Charlie", "email": "duplicate@example.com"},
        api_key="test-secret",
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "EMAIL_DUP"


def test_create_customer_invalid_email(client):
    response = post_json(
        client,
        "/customers",
        {"name": "Test", "email": "invalid-email"},
        api_key="test-secret",
    )
    assert response.status_code == 400


def test_create_customer_empty_name(client):
    response = post_json(
        client,
        "/customers",
        {"name": "", "email": "test@example.com"},
        api_key="test-secret",
    )
    assert response.status_code == 400
