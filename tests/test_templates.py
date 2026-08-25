"""Tests for the wpostgresql-mcp templates module."""

import os
from unittest import mock

import pytest

from wpostgresql_mcp.templates import TemplateGenerator


def test_get_supported_types():
    types = TemplateGenerator.get_supported_types()
    assert "standard" in types
    assert "api_service" in types


def test_get_folders_standard():
    folders = TemplateGenerator.get_folders("standard")
    assert "config" in folders
    assert "models" in folders
    assert "repositories" in folders
    assert "migrations" in folders
    assert "tests" in folders
    assert ".wpostgresql" in folders


def test_get_folders_api_service():
    folders = TemplateGenerator.get_folders("api_service")
    assert "config" in folders
    assert "models" in folders
    assert "repositories" in folders


def test_get_files_blueprint_standard():
    blueprints = TemplateGenerator.get_files_blueprint("standard", "my_project")
    assert "config/settings.py" in blueprints
    assert "models/user.py" in blueprints
    assert "models/post.py" in blueprints
    assert "repositories/user_repo.py" in blueprints
    assert "repositories/post_repo.py" in blueprints
    assert "migrations/manager.py" in blueprints
    assert "main.py" in blueprints
    assert "requirements.txt" in blueprints
    assert "README.md" in blueprints


def test_get_files_blueprint_api_service():
    blueprints = TemplateGenerator.get_files_blueprint("api_service", "my_project")
    reqs = blueprints["requirements.txt"]
    assert "fastapi" in reqs
    assert "uvicorn" in reqs
    assert "psycopg" in reqs


def test_blueprint_project_name_interpolation():
    blueprints = TemplateGenerator.get_files_blueprint("standard", "cool_app")
    assert "cool_app" in blueprints["README.md"].upper() or "COOL_APP" in blueprints["README.md"]


def test_blueprint_settings_has_from_env():
    blueprints = TemplateGenerator.get_files_blueprint("standard")
    settings = blueprints["config/settings.py"]
    assert "from_env" in settings
    assert "PG_DATABASE" in settings
    assert "PG_HOST" in settings


def test_blueprint_user_model_has_tablename():
    blueprints = TemplateGenerator.get_files_blueprint("standard")
    user_model = blueprints["models/user.py"]
    assert "__tablename__" in user_model
    assert "Primary Key" in user_model
    assert "NOT NULL" in user_model
    assert "UNIQUE" in user_model


def test_blueprint_migrations_has_tablesync():
    blueprints = TemplateGenerator.get_files_blueprint("standard")
    migrations = blueprints["migrations/manager.py"]
    assert "TableSync" in migrations
    assert "AsyncTableSync" in migrations
    assert "create_if_not_exists" in migrations
    assert "sync_with_model" in migrations
