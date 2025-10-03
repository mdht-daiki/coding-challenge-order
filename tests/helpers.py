from httpx import Response
from starlette.testclient import TestClient


def post_json(
    client: TestClient, path: str, payload: dict, *, api_key: str | None = None
) -> Response:
    headers = {}
    if api_key is not None:
        headers["X-API-KEY"] = api_key
    response = client.post(path, json=payload, headers=headers or None)
    assert (
        response.status_code < 500
    ), f"5xx from {path}: {response.status_code}, {response.text}"
    return response
