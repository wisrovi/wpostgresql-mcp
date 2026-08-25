"""Tests for the wpostgresql-mcp catalog module."""

import json
import logging
from unittest import mock

import pytest

from wpostgresql_mcp.catalog import PatternsCatalog


@pytest.fixture()
def catalog():
    with mock.patch.object(PatternsCatalog, "refresh_catalog", return_value=[]):
        return PatternsCatalog()


def test_init_loads_initial_catalog():
    c = PatternsCatalog()
    assert len(c.cached_patterns) == 20
    assert c.cached_patterns[0]["feature"] == "WPostgreSQL CRUD"


def test_fetch_url_success(catalog):
    payload = [{"name": "model_crud_basic"}]
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        resp = mock.MagicMock()
        resp.status = 200
        resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = resp

        result = catalog._fetch_url("https://example.com/catalog.json")
    assert result == payload


def test_fetch_url_non_200(catalog):
    with mock.patch("urllib.request.urlopen") as mock_urlopen:
        resp = mock.MagicMock()
        resp.status = 404
        mock_urlopen.return_value.__enter__.return_value = resp
        assert catalog._fetch_url("https://example.com/missing.json") == []


def test_fetch_url_exception(catalog, caplog):
    with mock.patch("urllib.request.urlopen", side_effect=Exception("boom")), caplog.at_level(logging.WARNING):
        assert catalog._fetch_url("https://example.com/bad.json") == []
    assert "Failed to fetch catalog" in caplog.text


def test_refresh_catalog_merges_sources(catalog):
    official = [{"name": "model_crud_basic"}]
    community = [{"name": "community_pattern"}]
    with mock.patch.object(catalog, "_fetch_url", side_effect=[official, community]) as mock_fetch:
        result = catalog.refresh_catalog()
    assert mock_fetch.call_count == 2
    assert len(result) == 2
    assert result[0]["origin"] == "Official"
    assert result[1]["origin"] == "Community"


def test_refresh_catalog_keeps_cache_when_empty(catalog):
    catalog.cached_patterns = [{"name": "keep_me", "origin": "Official"}]
    with mock.patch.object(catalog, "_fetch_url", return_value=[]):
        result = catalog.refresh_catalog()
    assert result == [{"name": "keep_me", "origin": "Official"}]


def test_search_matches_multiple_fields(catalog):
    patterns = [
        {"name": "model_crud_basic", "feature": "WPostgreSQL CRUD", "description": "auto table"},
        {"name": "async_ops", "feature": "Async WPostgreSQL", "description": "await-based"},
    ]
    catalog.cached_patterns = patterns
    assert len(catalog.search("crud")) == 1
    assert len(catalog.search("async")) == 1
    assert catalog.search("WPostgreSQL") == patterns


def test_search_case_insensitive(catalog):
    catalog.cached_patterns = [
        {"name": "TABLE_SYNC", "feature": "TableSync", "module": "x", "description": "d", "category": "c"}
    ]
    assert len(catalog.search("table_sync")) == 1
    assert len(catalog.search("TABLE_SYNC")) == 1


def test_search_empty_query_returns_all(catalog):
    catalog.cached_patterns = [{"name": "a"}, {"name": "b"}]
    assert len(catalog.search("")) == 2


def test_search_skips_missing_fields(catalog):
    catalog.cached_patterns = [{"name": "only_name"}, {"feature": "only_feature"}]
    assert len(catalog.search("only")) == 2
    assert catalog.search("nothing_here") == []


def test_search_triggers_refresh_when_empty(catalog):
    catalog.cached_patterns = []
    with mock.patch.object(catalog, "refresh_catalog") as mock_refresh:
        mock_refresh.return_value = [{"name": "fresh", "origin": "Official"}]
        catalog.search("fresh")
    mock_refresh.assert_called_once()
