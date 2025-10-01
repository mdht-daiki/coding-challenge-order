def test_create_customer_ok(client):
    response = client.post(
        "/customers", json={"name": "Alice", "email": "a@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cust_id"].startswith("C_")
    assert body["name"] == "Alice"
    assert body["email"] == "a@example.com"


def test_create_customer_duplicate_email(client):
    first_response = client.post(
        "/customers", json={"name": "Bob", "email": "duplicate@example.com"}
    )
    assert first_response.status_code == 200
    second_response = client.post(
        "/customers", json={"name": "Charlie", "email": "duplicate@example.com"}
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "EMAIL_DUP"


def test_create_customer_invalid_email(client):
    response = client.post(
        "/customers", json={"name": "Test", "email": "invalid-email"}
    )
    assert response.status_code == 422  # Validation error


def test_create_customer_empty_name(client):
    response = client.post("/customers", json={"name": "", "email": "test@example.com"})
    assert response.status_code == 422
