# tests/conftest.py
import copy
import logging.config
from datetime import date as _date

import pytest
from fastapi.testclient import TestClient

FIXED_TODAY = (2025, 10, 6)


def _get_logging_config():
    from app.main import LOGGING_CONFIG

    return LOGGING_CONFIG


@pytest.fixture
def frozen_today(monkeypatch):
    """
    app.services_orders モジュール内の date.today() を固定する。
    """

    class _FixedDate(_date):
        @classmethod
        def today(cls):
            y, m, d = FIXED_TODAY
            return cls(y, m, d)

    import app.services_orders as mod

    monkeypatch.setattr(mod, "date", _FixedDate, raising=True)
    yield


@pytest.fixture(autouse=True)
def set_api_key_env(monkeypatch):
    # テスト専用固定キー
    monkeypatch.setenv("API_KEY", "test-secret")
    monkeypatch.setenv("API_KEYS", "test-secret,new-test-key")
    monkeypatch.setenv("API_KEY_HASH_SECRET", "hash-secret")
    monkeypatch.setenv("TESTING", "true")
    yield


@pytest.fixture
def client():
    from app.main import app  # ← ここでだけ import

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def client_with_rate_limit(monkeypatch):
    """レート制限が有効なテストクライアント"""
    import importlib

    # レート制限を有効化
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("API_KEY", "test-secret")
    monkeypatch.setenv("API_KEY_HASH_SECRET", "hash-secret")

    from fastapi.testclient import TestClient

    import app.main as main_module

    # モジュールを再読み込みして新しいTESTING値を反映
    importlib.reload(main_module)

    try:
        with TestClient(main_module.app) as client:
            yield client
    finally:
        # テスト後は元の設定に戻す
        monkeypatch.setenv("TESTING", "true")
        importlib.reload(main_module)


@pytest.fixture(autouse=True)
def reset_storage():
    """各テストの前後でインメモリストレージを確実にクリア"""
    from app.core.auth import _blocked_ips, _failed_attempts
    from app.services_customers import _custid_by_email, _customers_by_id, _lock
    from app.services_orders import _lock_o, _orders_by_custid, _orders_by_id
    from app.services_products import _lock_p, _prodid_by_name, _products_by_id

    _blocked_ips.clear()
    _failed_attempts.clear()
    with _lock:
        _customers_by_id.clear()
        _custid_by_email.clear()
    with _lock_p:
        _products_by_id.clear()
        _prodid_by_name.clear()
    with _lock_o:
        _orders_by_id.clear()
        _orders_by_custid.clear()
    try:
        yield
    finally:
        _blocked_ips.clear()
        _failed_attempts.clear()
        with _lock:
            _customers_by_id.clear()
            _custid_by_email.clear()
        with _lock_p:
            _products_by_id.clear()
            _prodid_by_name.clear()
        with _lock_o:
            _orders_by_id.clear()
            _orders_by_custid.clear()


@pytest.fixture
def audit_log_file(tmp_path, monkeypatch, request):
    """ログファイルを一時ディレクトリに設定、テスト後に元に戻す"""
    log_file = tmp_path / "auth_audit.log"

    # 元の設定を保存 (deep copy)
    LOGGING_CONFIG = _get_logging_config()
    original_config = copy.deepcopy(LOGGING_CONFIG)

    # 一時的なログファイルパスに変更
    monkeypatch.setitem(LOGGING_CONFIG["handlers"]["file"], "filename", str(log_file))

    # ロギング設定を適用
    logging.config.dictConfig(LOGGING_CONFIG)

    # テスト終了後に元の設定を復元
    def restore_logging():
        logging.config.dictConfig(original_config)

    request.addfinalizer(restore_logging)

    return log_file
