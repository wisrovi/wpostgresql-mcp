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
            # --- Core CRUD & Multi-Table ---
            {
                "name": "ghost_table_audit",
                "feature": "Enterprise Ghost Table Audit Trail (_forensic_audit_log)",
                "module": "wpostgresql",
                "description": "Automatic creation and tracking of _forensic_audit_log ghost table recording before/after JSON snapshots and user audit metadata for all CRUD operations",
                "category": "Audit",
                "origin": "Official",
            },
            {
                "name": "multi_table_management",
                "feature": "Multi-Table Management",
                "module": "wpostgresql",
                "description": "WPostgreSQL([User, Product, Order], db_config) — Manage multiple database tables seamlessly from a single instance with db[User] indexing, db.product attribute access, and auto-routing",
                "category": "MultiTable",
                "origin": "Official",
            },
            {
                "name": "multi_table_auto_routing",
                "feature": "Auto-Routing Multi-Table Inserts",
                "module": "wpostgresql",
                "description": "db.insert(instance) — Automatically routes insert() and insert_async() to the registered table based on model type",
                "category": "MultiTable",
                "origin": "Official",
            },
            {
                "name": "model_crud_basic",
                "feature": "WPostgreSQL CRUD",
                "module": "wpostgresql",
                "description": "Pydantic model with automatic table creation, insert, get, update, delete",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "insert_and_read",
                "feature": "Insert and Read",
                "module": "wpostgresql",
                "description": "db.insert(Model(...)), db.get_all(), db.get_by_field(name='X')",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "update_with_basemodel",
                "feature": "Update with BaseModel",
                "module": "wpostgresql",
                "description": "db.update(id, Model(...)) — must pass BaseModel instance, NOT a dict",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "delete_by_id",
                "feature": "Delete by ID",
                "module": "wpostgresql",
                "description": "db.delete(record_id) — single record deletion by primary key",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "forensic_audit_model",
                "feature": "Forensic Audit & Soft Delete",
                "module": "wpostgresql",
                "description": "Inheriting from ForensicModel auto-manages audit columns (create_by, create_in, update_by, update_in, delete_by, delete_in, status=99)",
                "category": "Audit",
                "origin": "Official",
            },
            {
                "name": "soft_delete_audit",
                "feature": "Soft Delete & Audit Tracking",
                "module": "wpostgresql",
                "description": "db.delete(id, user_id=X) marks status=99 and audit metadata; use db.get_all(include_deleted=True) to include soft-deleted rows",
                "category": "Audit",
                "origin": "Official",
            },
            {
                "name": "double_underscore_operators",
                "feature": "Double Underscore Filters",
                "module": "wpostgresql",
                "description": "db.get_by_field(age__gt=25, city__like='%NY%') — gt, lt, gte, lte, like, in operators",
                "category": "Query",
                "origin": "Official",
            },
            # --- Pagination ---
            {
                "name": "pagination_limit_offset",
                "feature": "Limit/Offset Pagination",
                "module": "wpostgresql",
                "description": "db.get_paginated(limit=10, offset=0, order_by='name', order_desc=False)",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "pagination_page_number",
                "feature": "Page Number Pagination",
                "module": "wpostgresql",
                "description": "db.get_page(page=1, per_page=25) — 1-indexed page-based traversal",
                "category": "Performance",
                "origin": "Official",
            },
            # --- Batch Operations ---
            {
                "name": "batch_operations",
                "feature": "Batch Operations",
                "module": "wpostgresql",
                "description": "insert_many, update_many, delete_many in single transaction",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "insert_many",
                "feature": "Bulk Insert",
                "module": "wpostgresql",
                "description": "db.insert_many([Model(...), Model(...)]) — single transaction for multiple inserts",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "update_many",
                "feature": "Bulk Update",
                "module": "wpostgresql",
                "description": "db.update_many([(Model(...), id), ...]) — batch update with BaseModel instances",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "delete_many",
                "feature": "Bulk Delete",
                "module": "wpostgresql",
                "description": "db.delete_many([id1, id2, id3]) — batch delete by primary keys",
                "category": "Performance",
                "origin": "Official",
            },
            # --- Async ---
            {
                "name": "async_operations",
                "feature": "Async WPostgreSQL",
                "module": "wpostgresql",
                "description": "Await-based insert_async, get_all_async, get_by_field_async, update_async, delete_async",
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
                "name": "async_pagination",
                "feature": "Async Pagination",
                "module": "wpostgresql",
                "description": "get_paginated_async, get_page_async, count_async for async dataset traversal",
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
            # --- Transactions ---
            {
                "name": "transactions",
                "feature": "Transactions",
                "module": "wpostgresql",
                "description": "execute_transaction and with_transaction for atomic multi-operation",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "execute_transaction",
                "feature": "Raw SQL Transaction",
                "module": "wpostgresql",
                "description": "db.execute_transaction([(sql, params), ...]) — list of raw SQL + params tuples",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "with_transaction_callback",
                "feature": "Transaction Callback",
                "module": "wpostgresql",
                "description": "db.with_transaction(func) — callback receives Transaction object for atomic operations",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "transaction_context_manager",
                "feature": "Transaction Context Manager",
                "module": "wpostgresql.core.connection",
                "description": "get_transaction(db_config) / get_async_transaction(db_config) — auto-commit/auto-rollback",
                "category": "Advanced",
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
            # --- Connection Pooling ---
            {
                "name": "connection_pooling",
                "feature": "Connection Pooling",
                "module": "wpostgresql.core.connection",
                "description": "Global and per-instance connection pools via psycopg_pool with configurable min/max sizes",
                "category": "Performance",
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
                "name": "connection_manager_local",
                "feature": "Local ConnectionManager",
                "module": "wpostgresql.core.connection",
                "description": "Per-instance ConnectionManager and AsyncConnectionManager for isolated pool management",
                "category": "Performance",
                "origin": "Official",
            },
            {
                "name": "pooled_connection_context",
                "feature": "Pooled Connection Context",
                "module": "wpostgresql.core.connection",
                "description": "get_connection(db_config) / get_async_connection(db_config) — context-managed pooled connections",
                "category": "Performance",
                "origin": "Official",
            },
            # --- Schema ---
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
                "name": "index_management",
                "feature": "Index Management",
                "module": "wpostgresql.core.sync",
                "description": "TableSync.create_index, drop_index, get_indexes for explicit index control",
                "category": "Schema",
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
                "name": "table_info_inspection",
                "feature": "Table Info Inspection",
                "module": "wpostgresql.core.sync",
                "description": "sync.table_exists(), sync.get_columns(), sync.drop_table() — schema introspection",
                "category": "Schema",
                "origin": "Official",
            },
            # --- Query Builder ---
            {
                "name": "query_builder",
                "feature": "QueryBuilder",
                "module": "wpostgresql.builders",
                "description": "Type-safe SQL construction with WHERE, ORDER BY, LIMIT, OFFSET",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "query_builder_where_chain",
                "feature": "QueryBuilder WHERE Chain",
                "module": "wpostgresql.builders.query_builder",
                "description": "QueryBuilder('table').where('age', '>', 25).where('city', '=', 'NYC').build_select()",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "query_builder_delete",
                "feature": "QueryBuilder DELETE",
                "module": "wpostgresql.builders.query_builder",
                "description": "QueryBuilder('table').where('id', '=', 1).build_delete() — requires WHERE for safety",
                "category": "Query",
                "origin": "Official",
            },
            {
                "name": "query_builder_count",
                "feature": "QueryBuilder COUNT",
                "module": "wpostgresql.builders.query_builder",
                "description": "QueryBuilder('table').where('active', '=', True).build_count() — efficient count queries",
                "category": "Query",
                "origin": "Official",
            },
            # --- Security ---
            {
                "name": "sql_injection_prevention",
                "feature": "SQL Injection Prevention",
                "module": "wpostgresql.builders.query_builder",
                "description": "Regex-validated identifiers and parameterized queries for safe SQL construction",
                "category": "Security",
                "origin": "Official",
            },
            # --- Advanced Patterns ---
            {
                "name": "raw_sql_with_pool",
                "feature": "Raw SQL with Connection Pool",
                "module": "wpostgresql.core.connection",
                "description": "get_connection(db_config) for raw SQL execution through pooled connections",
                "category": "Advanced",
                "origin": "Official",
            },
            {
                "name": "multi_model_orchestration",
                "feature": "Multi-Model Orchestration",
                "module": "wpostgresql",
                "description": "Main.py wiring multiple Repository classes with shared DatabaseSettings and TableSync",
                "category": "Architecture",
                "origin": "Official",
            },
            {
                "name": "fastapi_integration",
                "feature": "FastAPI Integration",
                "module": "wpostgresql",
                "description": "Async WPostgreSQL with FastAPI routes, startup migration, and health check endpoint",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "environment_config",
                "feature": "Environment Config",
                "module": "config.settings",
                "description": "DatabaseSettings dataclass with from_env() classmethod for 12-factor config",
                "category": "Architecture",
                "origin": "Official",
            },
            {
                "name": "project_scaffold",
                "feature": "Project Scaffold",
                "module": "wpostgresql_mcp",
                "description": "deploy_wpostgresql_scaffolding for standard or api_service project structure",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "migration_psycopg2",
                "feature": "psycopg2 Migration",
                "module": "wpostgresql",
                "description": "Replace psycopg2 cursor/conn/close pattern with WPostgreSQL model-based CRUD",
                "category": "Migration",
                "origin": "Official",
            },
            {
                "name": "migration_sqlalchemy",
                "feature": "SQLAlchemy Migration",
                "module": "wpostgresql",
                "description": "Replace SQLAlchemy Base/Column/Session with Pydantic BaseModel + WPostgreSQL",
                "category": "Migration",
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
                "name": "cli_tool",
                "feature": "CLI Tool",
                "module": "wpostgresql.cli",
                "description": "wpostgresql CLI for init, list, insert, get, delete, count, drop, test-connection",
                "category": "Integration",
                "origin": "Official",
            },
            {
                "name": "database_views",
                "feature": "Database Views (@view)",
                "module": "wpostgresql",
                "description": "Declarative PostgreSQL Views via @view decorator with topological depends_on DDL ordering and read-only protection",
                "category": "Core",
                "origin": "Official",
            },
            {
                "name": "restore_from_sqlite",
                "feature": "Bidirectional SQLite Restore",
                "module": "wpostgresql",
                "description": "restore_from_sqlite and restore_from_sqlite_async to restore SQLite database backups into PostgreSQL",
                "category": "Backup",
                "origin": "Official",
            },

        ]
        with suppress(Exception):
            self.refresh_catalog()
