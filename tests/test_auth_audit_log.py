import json
from pathlib import Path

from tests.helpers import post_json


def test_auth_success_logs_to_audit_file(client):
    """認証成功時に監査ログが記録されることを確認"""
    log_file = Path("auth_audit.log")

    # ログファイルが存在する場合、既存の行数を記録
    initial_line_count = 0
    if log_file.exists():
        with open(log_file, "r") as f:
            initial_line_count = len(f.readlines())

    # 有効な API key でリクエスト
    response = post_json(
        client,
        "/customers",
        {"name": "TestUser", "email": "test@example.com"},
        api_key="test-secret",
    )
    assert response.status_code == 201

    # ログファイルに新しいエントリが追加されたことを確認
    assert log_file.exists(), "Audit log file should exist"

    with open(log_file, "r") as f:
        lines = f.readlines()
        new_lines = lines[initial_line_count:]

        # 最後のログエントリを検証
        assert len(new_lines) > 0, "New log entry should be written"
        last_log = json.loads(new_lines[-1])

        assert last_log["levelname"] == "INFO"
        assert "Authentication successful" in last_log["message"]
        assert "client_ip" in last_log
        assert "timestamp" in last_log


def test_auth_failure_missing_key_logs_to_audit_file(client):
    """API key が未指定の場合に監査ログが記録されることを確認"""
    log_file = Path("auth_audit.log")

    initial_line_count = 0
    if log_file.exists():
        with open(log_file, "r") as f:
            initial_line_count = len(f.readlines())

    # API key なしでリクエスト
    response = client.post(
        "/customers", json={"name": "TestUser", "email": "test@example.com"}
    )
    assert response.status_code == 401

    # ログファイルに新しいエントリが追加されたことを確認
    assert log_file.exists(), "Audit log file should exist"

    with open(log_file, "r") as f:
        lines = f.readlines()
        new_lines = lines[initial_line_count:]

        assert len(new_lines) > 0, "New log entry should be written"
        last_log = json.loads(new_lines[-1])

        assert last_log["levelname"] == "WARNING"
        assert "Authentication failed - missing API key" in last_log["message"]
        assert last_log["reason"] == "missing_header"
        assert "client_ip" in last_log


def test_auth_failure_invalid_key_logs_to_audit_file(client):
    """無効な API key の場合に監査ログが記録されることを確認"""
    log_file = Path("auth_audit.log")

    initial_line_count = 0
    if log_file.exists():
        with open(log_file, "r") as f:
            initial_line_count = len(f.readlines())

    # 無効な API key でリクエスト
    response = post_json(
        client,
        "/customers",
        {"name": "TestUser", "email": "test@example.com"},
        api_key="wrong-key",
    )
    assert response.status_code == 401

    # ログファイルに新しいエントリが追加されたことを確認
    assert log_file.exists(), "Audit log file should exist"

    with open(log_file, "r") as f:
        lines = f.readlines()
        new_lines = lines[initial_line_count:]

        assert len(new_lines) > 0, "New log entry should be written"
        last_log = json.loads(new_lines[-1])

        assert last_log["levelname"] == "WARNING"
        assert "Authentication failed - invalid API key" in last_log["message"]
        assert last_log["reason"] == "invalid_key"
        assert "client_ip" in last_log
