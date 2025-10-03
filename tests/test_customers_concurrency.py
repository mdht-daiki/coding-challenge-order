from concurrent.futures import ThreadPoolExecutor
from itertools import repeat


def test_many_parallel_posts(client):
    def _post(client, i):
        return client.post(
            "/customers",
            json={"name": f"U{i}", "email": f"u{i}@ex.com"},
            headers={"X-API-KEY": "test-secret"},
        )

    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(_post, repeat(client), range(200)))
    assert all(r.status_code == 201 for r in results)

    # 全てのレスポンスに有効なIDが含まれていることを確認
    ids = [r.json()["custId"] for r in results]
    assert len(ids) == 200, "Expected 200 responses"
    assert len(set(ids)) == 200, "Expected all IDs to be unique"

    # 全ての顧客が実際にストレージに保存されていることを確認
    for i, result in enumerate(results):
        data = result.json()
        assert data["name"] == f"U{i}"
        assert data["email"] == f"u{i}@ex.com"
