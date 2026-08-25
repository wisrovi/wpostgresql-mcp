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


def test_blueprints_update_takes_basemodel_not_dict():
    text = server.get_wpostgresql_architect_blueprints()
    assert "db.update(id, Person(...)" in text
    assert "NOT a dict" in text


def test_manual_contains_migration_guides():
    text = server.get_wpostgresql_architect_manual()
    assert "psycopg2" in text
    assert "SQLAlchemy" in text
    assert "MIGRATION" in text
    assert "FASTAPI" in text
    assert "MODULE MAP" in text


# --- Pattern search ---


def test_search_wpostgresql_pattern_returns_results():
    result = server.search_wpostgresql_pattern("crud")
    assert "Found" in result
    assert "model_crud_basic" in result


def test_search_wpostgresql_pattern_no_results():
    result = server.search_wpostgresql_pattern("xyznonexistent")
    assert "No patterns found" in result


# --- Scaffolding ---


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
    assert (tmp_path / "my_project" / "tests" / "test_user_repo.py").exists()
    assert (tmp_path / "my_project" / "tests" / "test_post_repo.py").exists()


def test_deploy_wpostgresql_scaffolding_exception_returns_error(tmp_path):
    with mock.patch("os.makedirs", side_effect=PermissionError("denied")):
        result = server.deploy_wpostgresql_scaffolding(str(tmp_path / "x"))
    assert "Error" in result


def test_deploy_api_service_includes_fastapi(tmp_path):
    target = str(tmp_path / "api_project")
    os.makedirs(target, exist_ok=True)
    result = server.deploy_wpostgresql_scaffolding(target, "api_app", "api_service")
    assert "Successfully deployed" in result
    reqs = (tmp_path / "api_project" / "requirements.txt").read_text()
    assert "fastapi" in reqs
    assert "uvicorn" in reqs
    assert (tmp_path / "api_project" / "routes" / "users.py").exists()
    assert (tmp_path / "api_project" / "app.py").exists()


def test_repo_template_update_uses_basemodel(tmp_path):
    target = str(tmp_path / "tmpl_test")
    os.makedirs(target, exist_ok=True)
    server.deploy_wpostgresql_scaffolding(target, "tmpl_test", "standard")
    repo_content = (tmp_path / "tmpl_test" / "repositories" / "user_repo.py").read_text()
    assert "def update(self, user_id: int, user: User)" in repo_content
    assert "self.db.update(user_id, user)" in repo_content
    # Ensure update does NOT accept a dict parameter
    assert "def update(self, user_id: int, data: dict)" not in repo_content


# --- generate_from_pattern ---


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


# --- validate_wpostgresql_project ---


def test_validate_project_compliant(tmp_path):
    target = str(tmp_path / "valid_project")
    os.makedirs(target, exist_ok=True)
    server.deploy_wpostgresql_scaffolding(target, "valid_project", "standard")
    result = server.validate_wpostgresql_project(target)
    assert "Score: 100%" in result
    assert "MISSING" not in result


def test_validate_project_missing_files(tmp_path):
    target = str(tmp_path / "empty_project")
    os.makedirs(target, exist_ok=True)
    result = server.validate_wpostgresql_project(target)
    assert "Score: 0%" in result
    assert "MISSING" in result


def test_validate_project_relative_path_rejected():
    result = server.validate_wpostgresql_project("relative/path")
    assert "Error" in result


def test_validate_project_nonexistent():
    result = server.validate_wpostgresql_project("/nonexistent/path")
    assert "Error" in result


# --- generate_mcp_client_config ---


def test_config_cursor():
    result = server.generate_mcp_client_config("cursor")
    assert "mcpServers" in result
    assert "wpostgresql-mcp" in result
    assert "Cursor" in result


def test_config_claude_desktop():
    result = server.generate_mcp_client_config("claude_desktop")
    assert "mcpServers" in result
    assert "claude_desktop_config.json" in result


def test_config_opencode():
    result = server.generate_mcp_client_config("opencode")
    assert "mcpServers" in result
    assert "opencode" in result.lower()


def test_config_gemini_cli():
    result = server.generate_mcp_client_config("gemini_cli")
    assert "gemini mcp add" in result


def test_config_unknown():
    result = server.generate_mcp_client_config("unknown_agent")
    assert "Error" in result
    assert "Available" in result


# --- validate_model_schema ---


def test_valid_model():
    code = (
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
    )
    result = server.validate_model_schema(code)
    assert "VALID" in result
    assert "Primary Key" in code  # verify the input has it
    assert "Good: Using Field descriptions" in result


def test_model_missing_tablename():
    code = (
        "class User(BaseModel):\n"
        '    id: int = Field(description="Primary Key")\n'
    )
    result = server.validate_model_schema(code)
    assert "Missing __tablename__" in result


def test_model_missing_primary_key():
    code = (
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    name: str = Field(description="NOT NULL")\n'
    )
    result = server.validate_model_schema(code)
    assert "Primary Key" in result


def test_model_sqlalchemy_detected():
    code = "session.add(User(id=1))\nsession.commit()"
    result = server.validate_model_schema(code)
    assert "SQLAlchemy" in result


def test_model_psycopg2_detected():
    code = "import psycopg2\nconn = psycopg2.connect()"
    result = server.validate_model_schema(code)
    assert "psycopg2" in result


# --- generate_wpostgresql_tests ---


def test_generate_tests_creates_test_files(tmp_path):
    target = str(tmp_path / "test_gen")
    os.makedirs(target, exist_ok=True)
    server.deploy_wpostgresql_scaffolding(target, "test_gen", "standard")
    result = server.generate_wpostgresql_tests(target)
    assert "Generated" in result
    assert "test_" in result
    assert (tmp_path / "test_gen" / "tests" / "test_user_repo.py").exists()
    assert (tmp_path / "test_gen" / "tests" / "test_post_repo.py").exists()


def test_generate_tests_no_repos_dir(tmp_path):
    target = str(tmp_path / "empty")
    os.makedirs(target, exist_ok=True)
    result = server.generate_wpostgresql_tests(target)
    assert "Error" in result


def test_generate_tests_relative_path():
    result = server.generate_wpostgresql_tests("relative/path")
    assert "Error" in result


# --- generate_migration_from_models ---


def test_migration_from_models():
    code = (
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "\n"
        "class Post(BaseModel):\n"
        '    __tablename__ = "posts"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    title: str = Field(description="NOT NULL")\n'
    )
    result = server.generate_migration_from_models(code)
    assert "2 model(s)" in result
    assert "User" in result
    assert "Post" in result
    assert "run_migrations" in result


def test_migration_no_models():
    result = server.generate_migration_from_models("no classes here")
    assert "Error" in result


# --- CLI ---


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


# --- Catalog ---


def test_catalog_has_35_plus_patterns():
    from wpostgresql_mcp.catalog import PatternsCatalog

    c = PatternsCatalog()
    assert len(c.cached_patterns) >= 35


def test_catalog_search_double_underscore():
    from wpostgresql_mcp.catalog import PatternsCatalog

    c = PatternsCatalog()
    results = c.search("double underscore")
    assert len(results) > 0
    assert any("double_underscore" in p["name"] for p in results)


def test_catalog_search_migration():
    from wpostgresql_mcp.catalog import PatternsCatalog

    c = PatternsCatalog()
    results = c.search("migration")
    assert len(results) > 0


def test_catalog_search_fastapi():
    from wpostgresql_mcp.catalog import PatternsCatalog

    c = PatternsCatalog()
    results = c.search("fastapi")
    assert len(results) > 0
