def post_json(client, path, payload):
    response = client.post(path, json=payload)
    assert (
        response.status_code < 500
    ), f"5xx from {path}: {response.status_code}, {response.text}"
    return response
