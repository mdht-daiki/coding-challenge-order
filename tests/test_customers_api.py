import pytest

from tests.helpers import post_json


@pytest.mark.parametrize("name", ["", " ", "A" * 101])
def test_create_customer_name_boundary(client, name):
    response = post_json(client, "/customers", {"name": name, "email": "b@example.com"})
    assert response.status_code in (400, 422)


def test_create_customer_ok(client):
    response = post_json(
        client, "/customers", {"name": "Alice", "email": "a@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["custId"].startswith("C_")
    assert body["name"] == "Alice"
    assert body["email"] == "a@example.com"


def test_create_customer_duplicate_email(client):
    first_response = post_json(
        client, "/customers", {"name": "Bob", "email": "duplicate@example.com"}
    )
    assert first_response.status_code == 200
    second_response = post_json(
        client, "/customers", {"name": "Charlie", "email": "duplicate@example.com"}
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "EMAIL_DUP"


def test_create_customer_invalid_email(client):
    response = post_json(
        client, "/customers", {"name": "Test", "email": "invalid-email"}
    )
    assert response.status_code == 422  # Validation error


def test_create_customer_empty_name(client):
    response = post_json(
        client, "/customers", {"name": "", "email": "test@example.com"}
    )
    assert response.status_code == 422
