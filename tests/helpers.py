from httpx import Response
from starlette.testclient import TestClient


def post_json(client: TestClient, path: str, payload: dict) -> Response:
    response = client.post(path, json=payload)
    assert (
        response.status_code < 500
    ), f"5xx from {path}: {response.status_code}, {response.text}"
    return response
