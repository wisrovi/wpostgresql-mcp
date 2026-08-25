"""Pattern catalog synchronization with local fallbacks for WPostgreSQL."""

import json
import logging
from contextlib import suppress
from urllib import request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class PatternsCatalog:
    """Manages the synchronization of available PostgreSQL patterns from the wisrovi SUITE.

    Synchronizes from GitHub just like the VS Code extension (with local fallbacks).
    """

    OFFICIAL_URL = "https://raw.githubusercontent.com/wisrovi/wpostgresql/main/patterns_catalog.json"
    COMMUNITY_URL = "https://raw.githubusercontent.com/wisrovi/wpostgresql-plugins/main/patterns_catalog.json"

    def __init__(self):
        """Initialize the catalog with hardcoded offline fallbacks."""
        self.cached_patterns = []
        self._load_initial_catalog()

    def _fetch_url(self, url: str) -> list:
        """Fetch patterns from a URL with timeout and error handling."""
        try:
            req = request.Request(url, headers={"User-Agent": "wpostgresql-mcp"})
            with request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, OSError) as e:
            logger.warning(f"Failed to fetch catalog from {url}: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Failed to fetch catalog from {url}: {e}")
        return []

    def refresh_catalog(self) -> list:
        """Fetch latest patterns from both official and community repositories."""
        official = self._fetch_url(self.OFFICIAL_URL)
        community = self._fetch_url(self.COMMUNITY_URL)

        all_patterns = []
        for p in official:
            p["origin"] = "Official"
            all_patterns.append(p)
        for p in community:
            p["origin"] = "Community"
            all_patterns.append(p)

        if all_patterns:
            self.cached_patterns = all_patterns
            logger.info(f"Catalog refreshed: {len(self.cached_patterns)} patterns found.")

        return self.cached_patterns

    def search(self, query: str) -> list:
        """Filters cataloged patterns based on a search query keyword."""
        if not self.cached_patterns:
            self.refresh_catalog()

        query_lower = query.lower()
        results = []
        for pattern in self.cached_patterns:
            fields = [
                pattern.get("name", ""),
                pattern.get("feature", ""),
                pattern.get("module", ""),
                pattern.get("description", ""),
                pattern.get("category", ""),
            ]
            if any(query_lower in str(f).lower() for f in fields):
                results.append(pattern)
        return results

    def _load_initial_catalog(self):
        """Initial load with hardcoded fallbacks if offline."""
        self.cached_patterns = [
            {
                "name": "model_crud_basic",
                "feature": "WPostgreSQL CRUD",
                "module": "wpostgresql",
                "description": "Pydantic model with automatic table creation, insert, get, update, delete",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "async_operations",
                "feature": "Async WPostgreSQL",
                "module": "wpostgresql",
                "description": "Await-based insert_async, get_all_async, get_by_field_async, update_async, delete_async",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "batch_operations",
                "feature": "Batch Operations",
                "module": "wpostgresql",
                "description": "insert_many, update_many, delete_many in single transaction",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "transactions",
                "feature": "Transactions",
                "module": "wpostgresql",
                "description": "execute_transaction and with_transaction for atomic multi-operation",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "query_builder",
                "feature": "QueryBuilder",
                "module": "wpostgresql.builders",
                "description": "Type-safe SQL construction with WHERE, ORDER BY, LIMIT, OFFSET",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "connection_pooling",
                "feature": "Connection Pooling",
                "module": "wpostgresql.core.connection",
                "description": "Global and per-instance connection pools via psycopg_pool with configurable min/max sizes",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "table_sync",
                "feature": "TableSync",
                "module": "wpostgresql.core.sync",
                "description": "Auto-create tables and sync schema from Pydantic models with ALTER TABLE ADD COLUMN",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "async_table_sync",
                "feature": "AsyncTableSync",
                "module": "wpostgresql.core.sync",
                "description": "Async schema synchronization with create_if_not_exists and sync_with_model",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "pagination",
                "feature": "Pagination",
                "module": "wpostgresql",
                "description": "get_page, get_paginated, count for large datasets with limit/offset",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "model_constraints",
                "feature": "Model Field Constraints",
                "module": "wpostgresql.types.sql_types",
                "description": "Primary key, unique, not null via Field description strings",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "index_management",
                "feature": "Index Management",
                "module": "wpostgresql.core.sync",
                "description": "TableSync.create_index, drop_index, get_indexes for explicit index control",
                "category": "Schema",
                "origin": "Official",
            },
            {
                "name": "sql_injection_prevention",
                "feature": "SQL Injection Prevention",
                "module": "wpostgresql.builders.query_builder",
                "description": "Regex-validated identifiers and parameterized queries for safe SQL construction",
                "category": "Security",
                "origin": "Official",
            },
            {
                "name": "global_pool_configuration",
                "feature": "Global Pool Configuration",
                "module": "wpostgresql.core.connection",
                "description": "configure_pool and close_global_pools for thread-safe singleton pool management",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "sync_and_async_duo",
                "feature": "Sync/Async Duality",
                "module": "wpostgresql",
                "description": "Every operation has both sync and async variants using psycopg 3",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "cli_tool",
                "feature": "CLI Tool",
                "module": "wpostgresql.cli",
                "description": "wpostgresql CLI for init, list, insert, get, delete, count, drop, test-connection",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "exception_hierarchy",
                "feature": "Exception Hierarchy",
                "module": "wpostgresql.exceptions",
                "description": "Structured exceptions: WPostgreSQLError, ConnectionError, TableSyncError, ValidationError, OperationError, SQLInjectionError, TransactionError",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "async_batch_operations",
                "feature": "Async Batch Operations",
                "module": "wpostgresql",
                "description": "insert_many_async, update_many_async, delete_many_async for bulk async writes",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "async_transactions",
                "feature": "Async Transactions",
                "module": "wpostgresql",
                "description": "execute_transaction_async, with_transaction_async for atomic async operations",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "async_pagination",
                "feature": "Async Pagination",
                "module": "wpostgresql",
                "description": "get_paginated_async, get_page_async, count_async for async dataset traversal",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "connection_manager_local",
                "feature": "Local ConnectionManager",
                "module": "wpostgresql.core.connection",
                "description": "Per-instance ConnectionManager and AsyncConnectionManager for isolated pool management",
                "category": "Performance",
                "origin": "Official",
            },
        ]
        with suppress(Exception):
            self.refresh_catalog()
