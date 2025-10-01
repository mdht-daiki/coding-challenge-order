import pytest
from fastapi.testclient import TestClient

from app import services
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_storage():
    """各テストの前にインメモリストレージをクリア"""
    services._customers_by_id.clear()
    if hasattr(services, "_custid_by_email"):
        services._custid_by_email.clear()
    yield
