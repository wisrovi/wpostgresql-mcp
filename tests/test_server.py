"""Tests for the wpostgresql-mcp server module."""

import json
import os
import signal
import sys
from pathlib import Path
from unittest import mock

import pytest

from wpostgresql_mcp import server


def test_get_catalog_returns_shared_singleton():
    server.get_catalog.cache_clear()
    c1 = server.get_catalog()
    c2 = server.get_catalog()
    assert c1 is c2
    server.get_catalog.cache_clear()


def test_blueprints_contains_all_10_sections():
    text = server.get_wpostgresql_architect_blueprints()
    sections = [
        "=== 1. COMPLETE CRUD OPERATIONS",
        "=== 2. PAGINATION",
        "=== 3. BATCH OPERATIONS",
        "=== 4. ASYNC OPERATIONS",
        "=== 5. TRANSACTIONS",
        "=== 6. CONNECTION POOLING",
        "=== 7. TABLE SYNC & SCHEMA MANAGEMENT",
        "=== 8. QUERY BUILDER",
        "=== 9. MODEL CONSTRAINTS & TYPE MAPPING",
        "=== 10. EXCEPTION HANDLING",
    ]
    for section in sections:
        assert section in text, f"Missing section: {section}"


def test_blueprints_has_real_newlines():
    text = server.get_wpostgresql_architect_blueprints()
    assert "\n" in text
    assert "WPostgreSQL" in text


def test_manual_contains_migration_guides():
    text = server.get_wpostgresql_architect_manual()
    assert "psycopg2" in text
    assert "SQLAlchemy" in text
    assert "MIGRATION" in text
    assert "FASTAPI" in text
    assert "MODULE MAP" in text


def test_blueprints_update_takes_basemodel_not_dict():
    text = server.get_wpostgresql_architect_blueprints()
    assert "db.update(id, Person(...)" in text
    assert "NOT a dict" in text


def test_search_wpostgresql_pattern_returns_results():
    result = server.search_wpostgresql_pattern("crud")
    assert "Found" in result
    assert "model_crud_basic" in result


def test_search_wpostgresql_pattern_no_results():
    result = server.search_wpostgresql_pattern("xyznonexistent")
    assert "No patterns found" in result


def test_deploy_wpostgresql_scaffolding_relative_path_rejected(tmp_path):
    result = server.deploy_wpostgresql_scaffolding("relative/path")
    assert "Error" in result
    assert "absolute path" in result


def test_deploy_wpostgresql_scaffolding_creates_project(tmp_path):
    target = str(tmp_path / "my_project")
    os.makedirs(target, exist_ok=True)
    result = server.deploy_wpostgresql_scaffolding(target, "test_project", "standard")
    assert "Successfully deployed" in result
    assert "test_project" in result
    assert (tmp_path / "my_project" / "config" / "settings.py").exists()
    assert (tmp_path / "my_project" / "models" / "user.py").exists()
    assert (tmp_path / "my_project" / "repositories" / "user_repo.py").exists()
    assert (tmp_path / "my_project" / "migrations" / "manager.py").exists()
    assert (tmp_path / "my_project" / "main.py").exists()


def test_deploy_wpostgresql_scaffolding_exception_returns_error(tmp_path):
    with mock.patch("os.makedirs", side_effect=PermissionError("denied")):
        result = server.deploy_wpostgresql_scaffolding(str(tmp_path / "x"))
    assert "Error" in result


def test_generate_from_pattern_success(tmp_path):
    target = str(tmp_path / "gen_project")
    os.makedirs(target, exist_ok=True)
    result = server.generate_from_pattern("model_crud_basic", target, "gen_app")
    assert "Successfully deployed" in result
    assert (tmp_path / "gen_project" / "examples" / "model_crud_basic_example.py").exists()


def test_generate_from_pattern_not_found(tmp_path):
    result = server.generate_from_pattern("nonexistent_pattern", str(tmp_path))
    assert "not found" in result


def test_generate_from_pattern_relative_path_rejected(tmp_path):
    result = server.generate_from_pattern("model_crud_basic", "relative/path")
    assert "Error" in result
    assert "absolute path" in result


def test_run_stdio_uses_stdio_transport():
    with mock.patch.object(server.mcp, "run") as mock_run:
        server.run_stdio()
    mock_run.assert_called_once_with(transport="stdio")


def test_run_sse_uses_sse_transport():
    with mock.patch.object(server.mcp, "run") as mock_run:
        server.run_sse()
    mock_run.assert_called_once_with(transport="sse")


def test_print_config_to_stdout(capsys, monkeypatch):
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    server.print_config(write_file=False)
    captured = capsys.readouterr()
    assert "mcpServers" in captured.out
    assert "wpostgresql-mcp" in captured.out


def test_print_config_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    server.print_config(write_file=True)
    config_path = tmp_path / ".agents" / "wpostgresql-mcp.json"
    assert config_path.exists()
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    assert "mcpServers" in config
    assert "wpostgresql-mcp" in config["mcpServers"]


def test_start_background_spawns_process(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "PID_FILE", str(tmp_path / ".wpostgresql_mcp.pid"))
    with (
        mock.patch("subprocess.Popen") as mock_popen,
        mock.patch("os.path.exists", return_value=False),
    ):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value.__enter__ = mock.MagicMock(return_value=mock_proc)
        mock_popen.return_value.__exit__ = mock.MagicMock(return_value=False)
        server.start_background()


def test_stop_background_kills_process(monkeypatch, tmp_path):
    pid_file = tmp_path / ".wpostgresql_mcp.pid"
    pid_file.write_text("99999")
    monkeypatch.setattr(server, "PID_FILE", str(pid_file))
    with mock.patch("os.kill") as mock_kill:
        server.stop_background()
    mock_kill.assert_called_once_with(99999, signal.SIGTERM)
    assert not pid_file.exists()


def test_stop_background_no_pid_file(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "PID_FILE", str(tmp_path / "nonexistent.pid"))
    server.stop_background()


def test_main_config_saves_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["wpostgresql-mcp", "config", "--print"])
    server.main()


def test_main_run_uses_stdio(monkeypatch):
    with mock.patch.object(server, "run_stdio") as mock_stdio:
        monkeypatch.setattr("sys.argv", ["wpostgresql-mcp", "run"])
        server.main()
    mock_stdio.assert_called_once()


def test_main_dispatches_commands(monkeypatch):
    with (
        mock.patch.object(server, "run_sse") as mock_sse,
        mock.patch.object(server, "start_background") as mock_start,
        mock.patch.object(server, "stop_background") as mock_stop,
    ):
        monkeypatch.setattr("sys.argv", ["wpostgresql-mcp", "run-sse"])
        server.main()
        mock_sse.assert_called_once()

        monkeypatch.setattr("sys.argv", ["wpostgresql-mcp", "start"])
        server.main()
        mock_start.assert_called_once()

        monkeypatch.setattr("sys.argv", ["wpostgresql-mcp", "stop"])
        server.main()
        mock_stop.assert_called_once()


def test_deploy_api_service_includes_fastapi(tmp_path):
    target = str(tmp_path / "api_project")
    os.makedirs(target, exist_ok=True)
    result = server.deploy_wpostgresql_scaffolding(target, "api_app", "api_service")
    assert "Successfully deployed" in result
    reqs = (tmp_path / "api_project" / "requirements.txt").read_text()
    assert "fastapi" in reqs
    assert "uvicorn" in reqs
    assert "psycopg" in reqs
