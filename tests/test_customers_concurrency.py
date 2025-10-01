from concurrent.futures import ThreadPoolExecutor
from itertools import repeat


def _post(client, i):
    return client.post("/customers", json={"name": f"U{i}", "email": f"u{i}@ex.com"})


def test_many_parallel_posts(client):
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(_post, repeat(client), range(200)))
    assert all(r.status_code == 200 for r in results)
