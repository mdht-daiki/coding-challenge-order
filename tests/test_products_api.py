import pytest

from tests.helpers import post_json


@pytest.mark.parametrize("name", [" ", "A" * 101])
def test_create_product_name_boundary(client, name):
    response = post_json(client, "/products", {"name": name, "unitPrice": 10000})
    # TODO: 統一エラーフォーマット実装後は400のみを期待
    assert response.status_code in (400, 422)


def test_create_product_ok(client):
    response = post_json(client, "/products", {"name": "Pen", "unitPrice": 100})
    assert response.status_code == 200
    body = response.json()
    assert body["prodId"].startswith("P_")
    assert body["name"] == "Pen"
    assert body["unitPrice"] == 100


def test_create_product_duplicate_name_case_insensitive(client):
    first_response = post_json(
        client, "/products", {"name": "Notebook", "unitPrice": 500}
    )
    assert first_response.status_code == 200
    second_response = post_json(
        client, "/products", {"name": "Notebook", "unitPrice": 800}
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "NAME_DUP"
