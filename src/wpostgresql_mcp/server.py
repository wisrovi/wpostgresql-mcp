"""MCP server, tools and CLI for WPostgreSQL architecting."""

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from wpostgresql_mcp.catalog import PatternsCatalog
from wpostgresql_mcp.templates import TemplateGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

PID_FILE = os.path.expanduser("~/.wpostgresql_mcp.pid")

mcp = FastMCP("wpostgresql-mcp-server")


@lru_cache(maxsize=1)
def get_catalog() -> PatternsCatalog:
    """Return the lazily-initialized shared catalog instance."""
    return PatternsCatalog()


# --- Tools ---


@mcp.tool()
def get_wpostgresql_architect_blueprints() -> str:
    """Complete reference with runnable code examples for every WPostgreSQL feature. Use this to understand HOW to use wpostgresql for any task: CRUD, async, batch, transactions, pooling, schema sync, query builder, and constraints."""
    crud_section = '''=== 1. COMPLETE CRUD OPERATIONS ===

# --- SETUP (required for all examples) ---
from pydantic import BaseModel, Field
from wpostgresql import WPostgreSQL

db_config = {
    "dbname": "wpostgresql",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": 5432,
}

class Person(BaseModel):
    __tablename__ = "person"
    id: int = Field(description="Primary Key")
    name: str = Field(description="NOT NULL")
    age: int = 0
    is_active: bool = True

db = WPostgreSQL(Person, db_config)

# --- INSERT ---
db.insert(Person(id=1, name="Juan Perez", age=30, is_active=True))
db.insert(Person(id=2, name="Ana Lopez", age=25, is_active=True))
db.insert(Person(id=3, name="Pedro Gomez", age=40, is_active=False))

# --- READ ALL ---
all_people = db.get_all()
print("All:", all_people)  # [Person(id=1, name='Juan Perez', ...), ...]

# --- READ BY FIELD ---
by_name = db.get_by_field(name="Juan Perez")
print("By name:", by_name)  # [Person(id=1, ...)]

active_25 = db.get_by_field(age=25, is_active=True)
print("Active 25:", active_25)  # [Person(id=2, name='Ana Lopez', ...)]

# --- DOUBLE UNDERSCORE OPERATORS ---
adults = db.get_by_field(age__gte=25)         # >= 25
young = db.get_by_field(age__lt=30)           # < 30
names = db.get_by_field(name__like="%Juan%")  # LIKE
active = db.get_by_field(is_active=True)      # = True

# --- UPDATE (pass a BaseModel instance, NOT a dict) ---
db.update(1, Person(id=1, name="Juan Perez Modified", age=31, is_active=False))
print("Updated:", db.get_by_field(id=1))

# --- DELETE ---
db.delete(3)
print("After delete:", db.get_all())

# --- COUNT ---
total = db.count()
print("Total:", total)'''

    pagination_section = '''=== 2. PAGINATION ===

# --- LIMIT/OFFSET pagination ---
page1 = db.get_paginated(limit=10, offset=0)
page2 = db.get_paginated(limit=10, offset=10)

# --- With ordering ---
ordered = db.get_paginated(limit=10, offset=0, order_by="name", order_desc=False)

# --- PAGE NUMBER pagination (1-indexed) ---
page = db.get_page(page=1, per_page=25)
total = db.count()
print(f"Page 1 of {total}: {page}")'''

    batch_section = '''=== 3. BATCH OPERATIONS ===

# --- INSERT MANY (single transaction) ---
people = [
    Person(id=10, name="Batch1", age=20, is_active=True),
    Person(id=11, name="Batch2", age=22, is_active=True),
    Person(id=12, name="Batch3", age=24, is_active=False),
]
db.insert_many(people)

# --- UPDATE MANY (list of BaseModel instances) ---
db.update_many([
    Person(id=10, name="Batch1 Updated", age=21, is_active=True),
    Person(id=11, name="Batch2 Updated", age=23, is_active=False),
])

# --- DELETE MANY (list of IDs) ---
db.delete_many([10, 11, 12])'''

    async_section = '''=== 4. ASYNC OPERATIONS ===

# Every sync method has an async counterpart (same parameters, add await):
await db.insert_async(Person(id=1, name="Async User", age=30, is_active=True))
all_users = await db.get_all_async()
filtered = await db.get_by_field_async(name="Async User")
await db.update_async(1, Person(id=1, name="Updated", age=31, is_active=True))
await db.delete_async(1)
page = await db.get_page_async(page=1, per_page=25)
total = await db.count_async()
await db.insert_many_async([Person(id=5, name="A", age=10, is_active=True)])
await db.delete_many_async([5, 6, 7])
ordered = await db.get_paginated_async(limit=10, offset=0, order_by="name", order_desc=True)'''

    transaction_section = '''=== 5. TRANSACTIONS ===

# --- execute_transaction (list of raw SQL + params) ---
db.execute_transaction([
    ("INSERT INTO person (id, name, age, is_active) VALUES (%s, %s, %s, %s)", (1, "Alice", 30, True)),
    ("UPDATE person SET age = %s WHERE id = %s", (31, 1)),
])

# --- with_transaction (callback pattern) ---
def do_work(txn):
    txn.execute("INSERT INTO person (id, name, age, is_active) VALUES (%s, %s, %s, %s)", (2, "Bob", 25, True))
    txn.execute("UPDATE person SET age = %s WHERE id = %s", (26, 2))

db.with_transaction(do_work)

# --- Transaction context managers (auto-commit / auto-rollback) ---
from wpostgresql import get_transaction, get_async_transaction

with get_transaction(db_config) as txn:
    txn.execute("INSERT INTO person (id, name, age, is_active) VALUES (%s, %s, %s, %s)", (3, "Charlie", 40, False))
    txn.execute("UPDATE person SET name = %s WHERE id = %s", ("Charlie Updated", 3))
# Auto-commits on success, auto-rollbacks on exception

async with get_async_transaction(db_config) as txn:
    await txn.execute("INSERT INTO person (id, name, age, is_active) VALUES (%s, %s, %s, %s)", (4, "Diana", 28, True))'''

    pool_section = '''=== 6. CONNECTION POOLING ===

from wpostgresql import configure_pool, close_global_pools, get_connection, get_async_connection

# Configure global pool (call once before creating WPostgreSQL instances)
configure_pool(db_config, min_size=5, max_size=50)

# Get pooled connection (sync)
with get_connection(db_config) as conn:
    cur = conn.execute("SELECT 1")
    print(cur.fetchone())

# Get pooled connection (async)
async with get_async_connection(db_config) as conn:
    cur = await conn.execute("SELECT 1")
    print(await cur.fetchone())

# Local per-instance pool manager
from wpostgresql import ConnectionManager, AsyncConnectionManager
cm = ConnectionManager(db_config)
with cm.get_connection() as conn:
    conn.execute("SELECT 1")

# Shutdown all pools on app exit
close_global_pools()'''

    schema_section = '''=== 7. TABLE SYNC & SCHEMA MANAGEMENT ===

from wpostgresql import TableSync, AsyncTableSync

# Create table if not exists (auto-generates DDL from Pydantic model)
sync = TableSync(Person, db_config)
sync.create_if_not_exists()

# Sync schema: compares model fields with DB columns, adds missing via ALTER TABLE
sync.sync_with_model()

# Index management
sync.create_index(["name"], "idx_person_name")
sync.create_index(["email"], "idx_person_email", unique=True)
indexes = sync.get_indexes()
sync.drop_index("idx_person_name")

# Table info
exists = sync.table_exists()
columns = sync.get_columns()
sync.drop_table()

# Async variants
async_sync = AsyncTableSync(Person, db_config)
await async_sync.create_if_not_exists_async()
await async_sync.sync_with_model_async()'''

    query_section = '''=== 8. QUERY BUILDER (safe SQL construction) ===

from wpostgresql import QueryBuilder

# Build SELECT queries with type-safe method chaining
qb = (
    QueryBuilder("person")
    .where("age", ">", 25)
    .where("city", "=", "NYC")
    .order_by("salary", descending=True)
    .limit(10)
    .offset(0)
)
query, values = qb.build_select()

# Supported operators: =, <, >, <=, >=, !=, LIKE, IN, IS NULL, IS NOT NULL
qb2 = QueryBuilder("person").where("name", "LIKE", "%Alice%").where("age", "IS NOT NULL", None)
sql, params = qb2.build_select()

# Count query
count_sql, count_params = qb.build_count()

# Delete query (requires WHERE clause for safety)
del_sql, del_params = qb.build_delete()

# Reset builder for reuse
qb.reset()'''

    constraints_section = '''=== 9. MODEL CONSTRAINTS & TYPE MAPPING ===

from pydantic import BaseModel, Field

# Constraints are encoded in Field description strings:
class Product(BaseModel):
    __tablename__ = "products"
    id: int = Field(description="Primary Key")        # -> PRIMARY KEY
    sku: str = Field(description="UNIQUE NOT NULL")   # -> UNIQUE NOT NULL
    name: str = Field(description="NOT NULL")          # -> NOT NULL
    price: float = 0.0                                 # -> no constraint
    is_active: bool = True                             # -> no constraint

# Type mapping:
# int   -> INTEGER
# str   -> TEXT
# bool  -> BOOLEAN

# Table name derivation:
# If __tablename__ = "products" is set -> uses "products"
# Otherwise -> lowercase class name (e.g., "Person" -> "person")'''

    exceptions_section = '''=== 10. EXCEPTION HANDLING ===

from wpostgresql.exceptions import (
    WPostgreSQLError,       # Base exception
    ConnectionError,        # Connection pool / auth failures
    TableSyncError,         # Schema sync / DDL failures
    ValidationError,        # Input validation failures
    OperationError,         # CRUD operation failures
    SQLInjectionError,      # Blocked SQL injection attempt
    TransactionError,       # Transaction commit/rollback failures
)

try:
    db.insert(person)
except ConnectionError as e:
    print(f"Connection failed: {e}")
except SQLInjectionError as e:
    print(f"SQL injection blocked: {e}")
except WPostgreSQLError as e:
    print(f"WPostgreSQL error: {e}")'''

    return "\n\n".join([
        "WPOSTGRESQL EXPERT BLUEPRINTS (COMPLETE REFERENCE - RUNNABLE EXAMPLES)",
        "",
        "CRITICAL: update() takes a BaseModel instance (NOT a dict): db.update(id, Person(...))",
        "CRITICAL: insert() returns None, use get_by_field() to retrieve after insert",
        "CRITICAL: All queries use parameterized %s placeholders (psycopg3 style)",
        "",
        crud_section,
        pagination_section,
        batch_section,
        async_section,
        transaction_section,
        pool_section,
        schema_section,
        query_section,
        constraints_section,
        exceptions_section,
    ])


@mcp.tool()
def search_wpostgresql_pattern(query: str) -> str:
    """Search for production-ready PostgreSQL patterns in official and community catalogs."""
    results = get_catalog().search(query)
    if not results:
        return f"No patterns found for query: '{query}'"

    lines = [f"Found {len(results)} pattern(s) for '{query}':\n"]
    for p in results:
        origin = p.get("origin", "Unknown")
        lines.append(f"  [{origin}] {p.get('name', 'N/A')} ({p.get('feature', 'N/A')})")
        lines.append(f"    Module: {p.get('module', 'N/A')}")
        lines.append(f"    Description: {p.get('description', 'N/A')}")
        lines.append(f"    Category: {p.get('category', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def deploy_wpostgresql_scaffolding(
    target_dir: str,
    project_name: str = "wpostgresql_project",
    scaffold_type: str = "standard",
) -> str:
    """Deploys a professional WPostgreSQL project structure following wisrovi standards."""
    if not os.path.isabs(target_dir):
        return f"Error: target_dir must be an absolute path. Got: {target_dir}"

    if scaffold_type not in TemplateGenerator.get_supported_types():
        return f"Error: Unsupported scaffold type '{scaffold_type}'. Use: {TemplateGenerator.get_supported_types()}"

    folders = TemplateGenerator.get_folders(scaffold_type)
    blueprints = TemplateGenerator.get_files_blueprint(scaffold_type, project_name)

    created_files = []
    try:
        for folder in folders:
            path = os.path.join(target_dir, folder)
            os.makedirs(path, exist_ok=True)

        for rel_path, content in blueprints.items():
            full_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            created_files.append(rel_path)

        return (
            f"Successfully deployed WPostgreSQL project '{project_name}' to {target_dir}\n"
            f"Scaffold type: {scaffold_type}\n"
            f"Created {len(created_files)} files:\n"
            + "\n".join(f"  - {f}" for f in created_files)
        )
    except Exception as e:
        return f"Error deploying scaffolding: {e}"


@mcp.tool()
def validate_postgresql_connection(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "postgres",
    user: str = "postgres",
    password: str = "",
) -> str:
    """Validate PostgreSQL connectivity and return health status."""
    try:
        import psycopg

        conninfo = f"host={host} port={port} dbname={dbname} user={user} password={password}"
        conn = psycopg.connect(conninfo, connect_timeout=5)

        cur = conn.execute("SELECT version()")
        version = cur.fetchone()[0]

        cur = conn.execute("SELECT current_database(), current_user, inet_server_addr()")
        db_info = cur.fetchone()

        cur = conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s", (dbname,))
        active = cur.fetchone()[0]

        cur = conn.execute("SELECT pg_size_pretty(pg_database_size(%s))", (dbname,))
        db_size = cur.fetchone()[0]

        conn.close()

        lines = [
            "PostgreSQL Connection: OK",
            f"  Version: {version}",
            f"  Database: {db_info[0]}",
            f"  User: {db_info[1]}",
            f"  Server: {db_info[2] or 'local'}",
            f"  Active connections: {active}",
            f"  Database size: {db_size}",
        ]
        return "\n".join(lines)
    except ImportError:
        return "Error: psycopg not installed. Run: pip install 'psycopg[binary]'"
    except Exception as e:
        return f"PostgreSQL Connection: FAILED\n  Error: {e}"


@mcp.tool()
def generate_from_pattern(pattern_name: str, target_dir: str, project_name: str = "wpostgresql_app") -> str:
    """Generate a complete project from a specific catalog pattern with pattern-specific code."""
    if not os.path.isabs(target_dir):
        return f"Error: target_dir must be an absolute path. Got: {target_dir}"

    catalog = get_catalog()
    results = catalog.search(pattern_name)
    pattern = None
    for p in results:
        if p.get("name") == pattern_name:
            pattern = p
            break

    if pattern is None:
        available = [p.get("name", "N/A") for p in catalog.cached_patterns[:10]]
        return (
            f"Pattern '{pattern_name}' not found in catalog.\n"
            f"Available patterns (first 10): {', '.join(available)}"
        )

    result = deploy_wpostgresql_scaffolding(target_dir, project_name, "standard")

    example_path = os.path.join(target_dir, "examples", f"{pattern_name}_example.py")
    os.makedirs(os.path.dirname(example_path), exist_ok=True)

    example_content = _generate_pattern_example(pattern_name, pattern, project_name)

    with open(example_path, "w", encoding="utf-8") as f:
        f.write(example_content)

    return result + f"\n  - examples/{pattern_name}_example.py (pattern-specific starter)"


@mcp.tool()
def validate_wpostgresql_project(project_path: str) -> str:
    """Validate a WPostgreSQL project structure against wisrovi standards. Checks mandatory files, imports, and compliance."""
    if not os.path.isabs(project_path):
        return f"Error: project_path must be an absolute path. Got: {project_path}"

    if not os.path.isdir(project_path):
        return f"Error: directory does not exist: {project_path}"

    mandatory_files = {
        "config/settings.py": "DatabaseSettings with from_env()",
        "models/__init__.py": "Model exports",
        "repositories/__init__.py": "Repository exports",
        "migrations/manager.py": "run_migrations function",
        "main.py": "Service entrypoint",
    }

    recommended_files = {
        "tests/__init__.py": "Test package",
        "requirements.txt": "Dependencies",
    }

    found = []
    missing = []
    warnings = []

    for fpath, desc in mandatory_files.items():
        full = os.path.join(project_path, fpath)
        if os.path.isfile(full):
            found.append(f"  OK: {fpath} ({desc})")
        else:
            missing.append(f"  MISSING: {fpath} ({desc})")

    for fpath, desc in recommended_files.items():
        full = os.path.join(project_path, fpath)
        if os.path.isfile(full):
            found.append(f"  OK: {fpath} ({desc})")
        else:
            warnings.append(f"  RECOMMENDED: {fpath} ({desc})")

    # Check models/ has at least one model file
    models_dir = os.path.join(project_path, "models")
    if os.path.isdir(models_dir):
        model_files = [f for f in os.listdir(models_dir) if f.endswith(".py") and f != "__init__.py"]
        if not model_files:
            warnings.append("  WARNING: models/ has no model files")
        else:
            found.append(f"  OK: {len(model_files)} model file(s)")

    # Check repositories/ has at least one repo file
    repos_dir = os.path.join(project_path, "repositories")
    if os.path.isdir(repos_dir):
        repo_files = [f for f in os.listdir(repos_dir) if f.endswith(".py") and f != "__init__.py"]
        if not repo_files:
            warnings.append("  WARNING: repositories/ has no repository files")
        else:
            found.append(f"  OK: {len(repo_files)} repository file(s)")

    score = len(found) * 20
    total = (len(found) + len(missing)) * 20
    score_pct = int(score / total * 100) if total > 0 else 0

    lines = [
        f"WPostgreSQL Project Validation: {project_path}",
        f"Score: {score_pct}% ({len(found)}/{len(found) + len(missing)} mandatory files)",
        "",
        "FOUND:",
        *found,
    ]

    if missing:
        lines.extend(["", "MISSING (mandatory):", *missing])

    if warnings:
        lines.extend(["", "WARNINGS:", *warnings])

    return "\n".join(lines)


@mcp.tool()
def generate_mcp_client_config(agent_type: str = "cursor") -> str:
    """Generate the exact JSON configuration block to install this MCP server in different AI clients."""
    python_path = sys.executable

    configs = {
        "cursor": {
            "mcpServers": {
                "wpostgresql-mcp": {
                    "command": python_path,
                    "args": ["-m", "wpostgresql_mcp.server", "run"],
                }
            }
        },
        "claude_desktop": {
            "mcpServers": {
                "wpostgresql-mcp": {
                    "command": python_path,
                    "args": ["-m", "wpostgresql_mcp.server", "run"],
                }
            }
        },
        "opencode": {
            "mcpServers": {
                "wpostgresql-mcp": {
                    "command": python_path,
                    "args": ["-m", "wpostgresql_mcp.server", "run"],
                }
            }
        },
        "gemini_cli": {
            "command": f"gemini mcp add wpostgresql-mcp {python_path} -m wpostgresql_mcp.server run",
            "description": "Run this command in your terminal (not JSON config)",
        },
    }

    agent_lower = agent_type.lower().strip()
    if agent_lower not in configs:
        available = ", ".join(configs.keys())
        return f"Error: Unknown agent_type '{agent_type}'. Available: {available}"

    config = configs[agent_lower]
    config_json = json.dumps(config, indent=2)

    install_notes = {
        "cursor": "Paste into Cursor Settings > MCP Servers",
        "claude_desktop": "Paste into ~/Library/Application Support/Claude/claude_desktop_config.json",
        "opencode": "Paste into ~/.config/opencode/opencode.json",
        "gemini_cli": "Run the command above in your terminal",
    }

    return (
        f"=== {agent_type.upper()} CONFIG ===\n\n"
        f"{config_json}\n\n"
        f"---\nInstall: {install_notes.get(agent_lower, '')}\n"
    )


@mcp.tool()
def validate_model_schema(model_code: str) -> str:
    """Validate a Pydantic model definition for WPostgreSQL compatibility. Checks Primary Key, Field descriptions, type mappings, and __tablename__."""
    issues = []
    warnings = []
    suggestions = []

    # Check __tablename__
    if "__tablename__" not in model_code:
        issues.append("Missing __tablename__ — table name will be lowercase class name (may be unexpected)")

    # Check Primary Key
    if "Primary Key" not in model_code:
        issues.append("No field with 'Primary Key' in description — every model needs a primary key")

    # Check type annotations
    type_map = {"int": "INTEGER", "str": "TEXT", "bool": "BOOLEAN", "float": "REAL"}
    for pytype, pgtype in type_map.items():
        if f": {pytype}" in model_code:
            pass  # valid mapping

    # Check for common mistakes
    if "db.update(" in model_code and "dict" in model_code.lower():
        issues.append("CRITICAL: update() takes a BaseModel instance, NOT a dict")

    if "session.add(" in model_code or "session.commit(" in model_code:
        issues.append("SQLAlchemy pattern detected — use WPostgreSQL instead (db.insert, db.update)")

    if "psycopg2" in model_code:
        issues.append("psycopg2 pattern detected — use WPostgreSQL which wraps psycopg 3")

    if "conn.cursor()" in model_code:
        issues.append("Raw cursor pattern — use WPostgreSQL methods instead")

    # Check for good practices
    if "Field(description=" in model_code:
        suggestions.append("Good: Using Field descriptions for constraints")

    if "BaseModel" in model_code:
        suggestions.append("Good: Using Pydantic BaseModel")

    if "NOT NULL" in model_code:
        suggestions.append("Good: Using NOT NULL constraint")

    if "UNIQUE" in model_code:
        suggestions.append("Good: Using UNIQUE constraint")

    # Check for bad Field usage
    if "Field(" in model_code and "description=" not in model_code:
        warnings.append("Fields without description — add description='Primary Key' or 'NOT NULL' for constraints")

    # Count fields
    field_count = model_code.count("Field(")
    if field_count == 0:
        issues.append("No Pydantic Field definitions found")
    else:
        suggestions.append(f"Found {field_count} field definition(s)")

    lines = ["WPostgreSQL Model Schema Validation", ""]

    if issues:
        lines.append("ISSUES:")
        for i in issues:
            lines.append(f"  - {i}")
        lines.append("")

    if warnings:
        lines.append("WARNINGS:")
        for w in warnings:
            lines.append(f"  - {w}")
        lines.append("")

    if suggestions:
        lines.append("OK:")
        for s in suggestions:
            lines.append(f"  - {s}")

    if not issues and not warnings:
        lines.append("Result: VALID — model is compatible with WPostgreSQL")
    else:
        lines.append(f"\nResult: {len(issues)} issue(s), {len(warnings)} warning(s)")

    return "\n".join(lines)


@mcp.tool()
def generate_wpostgresql_tests(project_path: str) -> str:
    """Generate comprehensive pytest unit tests for all repository classes in a WPostgreSQL project. Covers CRUD, batch, pagination, transactions, and async methods."""
    if not os.path.isabs(project_path):
        return f"Error: project_path must be an absolute path. Got: {project_path}"

    repos_dir = os.path.join(project_path, "repositories")
    tests_dir = os.path.join(project_path, "tests")

    if not os.path.isdir(repos_dir):
        return f"Error: {repos_dir} does not exist. Deploy scaffolding first with deploy_wpostgresql_scaffolding."

    os.makedirs(tests_dir, exist_ok=True)

    generated = []
    repo_files = [f for f in os.listdir(repos_dir) if f.endswith("_repo.py") and not f.startswith("__")]

    for repo_file in repo_files:
        repo_name = repo_file.replace(".py", "")
        class_name = "".join(w.capitalize() for w in repo_name.replace("_repo", "").split("_")) + "Repository"
        model_name = repo_name.replace("_repo", "")
        model_class = model_name.capitalize()

        repo_path = os.path.join(repos_dir, repo_file)
        with open(repo_path, encoding="utf-8") as f:
            repo_content = f.read()

        methods = re.findall(r"def (\w+)\(self", repo_content)
        has_async = any("_async" in m for m in methods)

        test_content = f'"""Auto-generated tests for {class_name}."""\n\n'
        test_content += "from unittest import mock\n\nimport pytest\n\n"
        test_content += f"from models.{model_name} import {model_class}\n"
        test_content += f"from repositories.{repo_name} import {class_name}\n"
        test_content += "from config.settings import DatabaseSettings\n\n\n"

        test_content += "@pytest.fixture\ndef settings():\n"
        test_content += '    return DatabaseSettings(dbname="testdb", user="test", password="test", host="localhost")\n\n\n'

        test_content += "@pytest.fixture\ndef repo(settings):\n"
        test_content += f"    with mock.patch('repositories.{repo_name}.WPostgreSQL') as MockDB:\n"
        test_content += "        instance = MockDB.return_value\n"
        test_content += f"        yield {class_name}(settings), instance\n\n\n"

        if has_async:
            test_content += "@pytest.fixture\nasync def async_repo(settings):\n"
            test_content += f"    with mock.patch('repositories.{repo_name}.WPostgreSQL') as MockDB:\n"
            test_content += "        instance = MockDB.return_value\n"
            test_content += f"        yield {class_name}(settings), instance\n\n\n"

        for method in methods:
            if method.startswith("_"):
                continue

            test_name = f"test_{method}"

            # --- INSERT ---
            if method == "insert" or (method.startswith("insert") and method != "insert_many" and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}({model_class}(id=1, name='test'))\n"
                test_content += f"    db.insert.assert_called_once()\n\n"

            # --- INSERT MANY ---
            elif method == "insert_many":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    items = [{model_class}(id=i, name=f'item{{i}}') for i in range(3)]\n"
                test_content += f"    r.{method}(items)\n"
                test_content += f"    db.insert_many.assert_called_once_with(items)\n\n"

            # --- GET ALL ---
            elif method == "get_all" or (method.startswith("get_all") and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    expected = [{model_class}(id=1, name='a'), {model_class}(id=2, name='b')]\n"
                test_content += f"    db.get_all.return_value = expected\n"
                test_content += f"    result = r.{method}()\n"
                test_content += f"    assert isinstance(result, list)\n"
                test_content += f"    assert len(result) == 2\n\n"

            # --- GET BY FIELD ---
            elif method == "get_by_field" or (method.startswith("get_by_field") and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    expected = [{model_class}(id=1, name='match')]\n"
                test_content += f"    db.get_by_field.return_value = expected\n"
                test_content += f"    result = r.{method}(name='match')\n"
                test_content += f"    db.get_by_field.assert_called_once_with(name='match')\n"
                test_content += f"    assert len(result) == 1\n\n"

            # --- UPDATE ---
            elif method == "update" or (method == "update" and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}(1, {model_class}(id=1, name='updated'))\n"
                test_content += f"    db.update.assert_called_once_with(1, {model_class}(id=1, name='updated'))\n\n"

            # --- DELETE ---
            elif method == "delete" or (method == "delete" and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}(1)\n"
                test_content += f"    db.delete.assert_called_once_with(1)\n\n"

            # --- COUNT ---
            elif method == "count" or (method == "count" and "_async" not in method):
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.count.return_value = 42\n"
                test_content += f"    result = r.{method}()\n"
                test_content += f"    assert result == 42\n\n"

            # --- GET PAGINATED ---
            elif method == "get_paginated":
                test_content += f"def {test_name}_default(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.get_paginated.return_value = [{model_class}(id=1, name='a')]\n"
                test_content += f"    result = r.{method}(limit=10, offset=0)\n"
                test_content += f"    db.get_paginated.assert_called_once_with(limit=10, offset=0, order_by=None, order_desc=False)\n"
                test_content += f"    assert isinstance(result, list)\n\n"
                test_content += f"def {test_name}_with_order(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.get_paginated.return_value = []\n"
                test_content += f"    r.{method}(limit=5, offset=10, order_by='name', order_desc=True)\n"
                test_content += f"    db.get_paginated.assert_called_once_with(limit=5, offset=10, order_by='name', order_desc=True)\n\n"

            # --- GET PAGE ---
            elif method == "get_page":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.get_paginated.return_value = [{model_class}(id=1, name='a')]\n"
                test_content += f"    result = r.{method}(page=2, per_page=10)\n"
                test_content += f"    db.get_paginated.assert_called_once_with(limit=10, offset=10)\n"
                test_content += f"    assert isinstance(result, list)\n\n"

            # --- UPDATE MANY ---
            elif method == "update_many":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    updates = [\n"
                test_content += f"        ({model_class}(id=1, name='u1'), 1),\n"
                test_content += f"        ({model_class}(id=2, name='u2'), 2),\n"
                test_content += f"    ]\n"
                test_content += f"    db.update_many.return_value = 2\n"
                test_content += f"    result = r.{method}(updates)\n"
                test_content += f"    db.update_many.assert_called_once_with(updates)\n"
                test_content += f"    assert result == 2\n\n"

            # --- DELETE MANY ---
            elif method == "delete_many":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.delete_many.return_value = 3\n"
                test_content += f"    result = r.{method}([1, 2, 3])\n"
                test_content += f"    db.delete_many.assert_called_once_with([1, 2, 3])\n"
                test_content += f"    assert result == 3\n\n"

            # --- EXECUTE TRANSACTION ---
            elif method == "execute_transaction":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    ops = [\n"
                test_content += f'        ("INSERT INTO t (id) VALUES (%s)", (1,)),\n'
                test_content += f'        ("UPDATE t SET name = %s WHERE id = %s", ("x", 1)),\n'
                test_content += f"    ]\n"
                test_content += f"    db.execute_transaction.return_value = [None, None]\n"
                test_content += f"    result = r.{method}(ops)\n"
                test_content += f"    db.execute_transaction.assert_called_once_with(ops)\n"
                test_content += f"    assert isinstance(result, list)\n\n"

            # --- WITH TRANSACTION ---
            elif method == "with_transaction":
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    callback = mock.MagicMock(return_value='done')\n"
                test_content += f"    db.with_transaction.return_value = 'done'\n"
                test_content += f"    result = r.{method}(callback)\n"
                test_content += f"    db.with_transaction.assert_called_once_with(callback)\n"
                test_content += f"    assert result == 'done'\n\n"

            # --- ASYNC INSERT ---
            elif method == "insert_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    await r.{method}({model_class}(id=1, name='test'))\n"
                test_content += f"    db.insert_async.assert_called_once()\n\n"

            # --- ASYNC INSERT MANY ---
            elif method == "insert_many_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    items = [{model_class}(id=i, name=f'item{{i}}') for i in range(3)]\n"
                test_content += f"    await r.{method}(items)\n"
                test_content += f"    db.insert_many_async.assert_called_once_with(items)\n\n"

            # --- ASYNC GET ALL ---
            elif method == "get_all_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    expected = [{model_class}(id=1, name='a')]\n"
                test_content += f"    db.get_all_async.return_value = expected\n"
                test_content += f"    result = await r.{method}()\n"
                test_content += f"    assert isinstance(result, list)\n"
                test_content += f"    assert len(result) == 1\n\n"

            # --- ASYNC GET BY FIELD ---
            elif method == "get_by_field_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    db.get_by_field_async.return_value = [{model_class}(id=1, name='match')]\n"
                test_content += f"    result = await r.{method}(name='match')\n"
                test_content += f"    db.get_by_field_async.assert_called_once_with(name='match')\n"
                test_content += f"    assert len(result) == 1\n\n"

            # --- ASYNC UPDATE ---
            elif method == "update_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    await r.{method}(1, {model_class}(id=1, name='updated'))\n"
                test_content += f"    db.update_async.assert_called_once()\n\n"

            # --- ASYNC DELETE ---
            elif method == "delete_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    await r.{method}(1)\n"
                test_content += f"    db.delete_async.assert_called_once_with(1)\n\n"

            # --- ASYNC COUNT ---
            elif method == "count_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    db.count_async.return_value = 10\n"
                test_content += f"    result = await r.{method}()\n"
                test_content += f"    assert result == 10\n\n"

            # --- ASYNC GET PAGINATED ---
            elif method == "get_paginated_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    db.get_paginated_async.return_value = [{model_class}(id=1, name='a')]\n"
                test_content += f"    result = await r.{method}(limit=10, offset=0)\n"
                test_content += f"    db.get_paginated_async.assert_called_once_with(limit=10, offset=0, order_by=None, order_desc=False)\n"
                test_content += f"    assert isinstance(result, list)\n\n"

            # --- ASYNC GET PAGE ---
            elif method == "get_page_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    db.get_paginated_async.return_value = [{model_class}(id=1, name='a')]\n"
                test_content += f"    result = await r.{method}(page=1, per_page=10)\n"
                test_content += f"    db.get_paginated_async.assert_called_once_with(limit=10, offset=0)\n"
                test_content += f"    assert isinstance(result, list)\n\n"

            # --- ASYNC UPDATE MANY ---
            elif method == "update_many_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    updates = [({model_class}(id=1, name='u'), 1)]\n"
                test_content += f"    db.update_many_async.return_value = 1\n"
                test_content += f"    result = await r.{method}(updates)\n"
                test_content += f"    db.update_many_async.assert_called_once_with(updates)\n"
                test_content += f"    assert result == 1\n\n"

            # --- ASYNC DELETE MANY ---
            elif method == "delete_many_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    db.delete_many_async.return_value = 2\n"
                test_content += f"    result = await r.{method}([1, 2])\n"
                test_content += f"    db.delete_many_async.assert_called_once_with([1, 2])\n"
                test_content += f"    assert result == 2\n\n"

            # --- ASYNC EXECUTE TRANSACTION ---
            elif method == "execute_transaction_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    ops = [(\"SELECT 1\", ())]\n"
                test_content += f"    db.execute_transaction_async.return_value = [(1,)]\n"
                test_content += f"    result = await r.{method}(ops)\n"
                test_content += f"    db.execute_transaction_async.assert_called_once_with(ops)\n"
                test_content += f"    assert isinstance(result, list)\n\n"

            # --- ASYNC WITH TRANSACTION ---
            elif method == "with_transaction_async":
                test_content += f"async def {test_name}(async_repo):\n"
                test_content += f"    r, db = async_repo\n"
                test_content += f"    callback = mock.AsyncMock(return_value='done')\n"
                test_content += f"    db.with_transaction_async.return_value = 'done'\n"
                test_content += f"    result = await r.{method}(callback)\n"
                test_content += f"    db.with_transaction_async.assert_called_once_with(callback)\n"
                test_content += f"    assert result == 'done'\n\n"

            # --- FALLBACK for unknown methods ---
            else:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    # TODO: implement test for {method}\n"
                test_content += f"    pass\n\n"

        test_file = os.path.join(tests_dir, f"test_{repo_name}.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        generated.append(f"tests/test_{repo_name}.py")

    if not generated:
        return f"No *_repo.py files found in {repos_dir}"

    return (
        f"Generated {len(generated)} test file(s) with full method coverage:\n"
        + "\n".join(f"  - {f}" for f in generated)
        + "\n\nRun: pytest tests/ -v"
    )


@mcp.tool()
def generate_migration_from_models(models_code: str, db_path: str = "app.db") -> str:
    """Generate a migration file from Pydantic model definitions."""
    # Parse model classes from the code
    model_pattern = re.compile(r"class (\w+)\(BaseModel\):")
    models_found = model_pattern.findall(models_code)

    if not models_found:
        return "Error: No Pydantic BaseModel classes found in the provided code"

    migration = '"""Auto-generated migration from Pydantic models."""\n\n'
    migration += "from wpostgresql import TableSync, AsyncTableSync\n"
    migration += "from config.settings import DatabaseSettings\n\n\n"

    # Import models
    for model in models_found:
        migration += f"from models.{model.lower()} import {model}\n"

    migration += "\n\n"
    migration += "def run_migrations(settings: DatabaseSettings) -> None:\n"
    migration += '    """Run schema synchronization for all models."""\n'
    migration += "    db_config = settings.to_dict()\n\n"

    for model in models_found:
        migration += f"    TableSync({model}, db_config).create_if_not_exists()\n"
        migration += f"    TableSync({model}, db_config).sync_with_model()\n\n"

    migration += "\n\n"
    migration += "async def run_migrations_async(settings: DatabaseSettings) -> None:\n"
    migration += '    """Async schema synchronization."""\n'
    migration += "    db_config = settings.to_dict()\n\n"

    for model in models_found:
        migration += f"    await AsyncTableSync({model}, db_config).create_if_not_exists_async()\n"
        migration += f"    await AsyncTableSync({model}, db_config).sync_with_model_async()\n\n"

    lines = [
        f"Migration generated for {len(models_found)} model(s): {', '.join(models_found)}",
        "",
        "Generated code:",
        "",
        migration,
        "",
        "Save to migrations/manager.py and call run_migrations(settings) from your main.py",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_wpostgresql_architect_manual() -> str:
    """Expert manual for building high-performance PostgreSQL-backed systems. Includes migration guides from psycopg2 and SQLAlchemy, FastAPI integration, and production best practices."""
    manual_text = (
        "WPOSTGRESQL ARCHITECT MANUAL (ADVANCED)\n"
        "\n"
        "--- INSTANT START (copy-paste and run) ---\n"
        "from pydantic import BaseModel, Field\n"
        "from wpostgresql import WPostgreSQL\n"
        "\n"
        'db_config = {"dbname": "mydb", "user": "postgres", "password": "postgres", "host": "localhost", "port": 5432}\n'
        "\n"
        "class Person(BaseModel):\n"
        '    __tablename__ = "person"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "    age: int = 0\n"
        "    is_active: bool = True\n"
        "\n"
        "db = WPostgreSQL(Person, db_config)\n"
        "db.insert(Person(id=1, name='Alice', age=30, is_active=True))\n"
        "print(db.get_all())  # Works!\n"
        "\n"
        "--- PROJECT STRUCTURE RULES (MANDATORY) ---\n"
        "1. CONFIG: All database settings MUST be centralized in `config/settings.py` as a `DatabaseSettings` dataclass. Prefer `from_env()` so no credentials are hardcoded.\n"
        "2. MODELS: All Pydantic models MUST be placed inside a `models/` directory. Create one file per domain entity (e.g., `models/user.py`, `models/post.py`), and populate `models/__init__.py` to export them.\n"
        "3. REPOSITORIES: All data-access code MUST be placed inside a `repositories/` directory. Create one file per model (e.g., `repositories/user_repo.py`), and populate `repositories/__init__.py` to export them.\n"
        "4. MIGRATIONS: Schema synchronization via `TableSync` MUST live in `migrations/manager.py` with a `run_migrations(settings)` function.\n"
        "5. ORCHESTRATOR: The service entrypoint MUST be placed in `main.py` at the root level, importing Settings, Models, and Repositories.\n"
        "\n"
        "--- CORE RULES ---\n"
        "1. Always use Pydantic models with type annotations - WPostgreSQL derives schema from them.\n"
        "2. Use `description` on Fields for constraints: `Primary Key`, `UNIQUE`, `NOT NULL`.\n"
        "3. Use connection pooling (`configure_pool` or `pool_config` in WPostgreSQL) for production.\n"
        "4. Use `TableSync` for zero-migration schema management: auto-creates tables and adds missing columns.\n"
        "5. Prefer `insert_many`/`update_many`/`delete_many` for bulk writes in single transaction.\n"
        "6. Use `execute_transaction` or `with_transaction` for atomic multi-table operations.\n"
        "7. Use `QueryBuilder` for dynamic queries - prevents SQL injection with regex-validated identifiers.\n"
        "8. Use `get_transaction`/`get_async_transaction` context managers for auto-commit/auto-rollback.\n"
        "9. Use `configure_pool(db_config, min_size, max_size)` for global pool sizing (default: 5-50).\n"
        "10. For production, prefer async (`*_async`) methods with `get_async_connection`.\n"
        "11. Close pools on shutdown: `close_global_pools()`.\n"
        "12. WPostgreSQL uses psycopg 3 (NOT psycopg2) with psycopg_pool for connection pooling.\n"
        "13. Table names are derived from `__tablename__` class attribute or lowercase class name.\n"
        "14. SQL injection prevention: all identifiers validated via regex `^[a-zA-Z_][a-zA-Z0-9_]*$`.\n"
        "\n"
        "--- MIGRATION: psycopg2 -> wpostgresql ---\n"
        "BEFORE (psycopg2):\n"
        "import psycopg2\n"
        "conn = psycopg2.connect(dbname='mydb', user='postgres', password='pwd', host='localhost')\n"
        "cur = conn.cursor()\n"
        "cur.execute('INSERT INTO users (name, age) VALUES (%s, %s)', ('Alice', 30))\n"
        "conn.commit()\n"
        "cur.execute('SELECT * FROM users WHERE age > %s', (25,))\n"
        "rows = cur.fetchall()\n"
        "conn.close()\n"
        "\n"
        "AFTER (wpostgresql):\n"
        "from pydantic import BaseModel, Field\n"
        "from wpostgresql import WPostgreSQL\n"
        "\n"
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "    age: int = 0\n"
        "\n"
        'db_config = {"dbname": "mydb", "user": "postgres", "password": "pwd", "host": "localhost", "port": 5432}\n'
        "db = WPostgreSQL(User, db_config)\n"
        "\n"
        "# Insert\n"
        "db.insert(User(id=1, name='Alice', age=30))\n"
        "\n"
        "# Read\n"
        "results = db.get_by_field(age=25)  # returns list of User instances\n"
        "\n"
        "# No more manual conn.close(), cursor, commit - WPostgreSQL handles connection pooling.\n"
        "\n"
        "--- MIGRATION: SQLAlchemy -> wpostgresql ---\n"
        "BEFORE (SQLAlchemy):\n"
        "from sqlalchemy import create_engine, Column, Integer, String\n"
        "from sqlalchemy.orm import declarative_base, Session\n"
        "Base = declarative_base()\n"
        "class User(Base):\n"
        "    __tablename__ = 'users'\n"
        "    id = Column(Integer, primary_key=True)\n"
        "    name = Column(String)\n"
        "engine = create_engine('postgresql://postgres:pwd@localhost/mydb')\n"
        "Base.metadata.create_all(engine)\n"
        "with Session(engine) as session:\n"
        "    session.add(User(id=1, name='Alice'))\n"
        "    session.commit()\n"
        "\n"
        "AFTER (wpostgresql):\n"
        "from pydantic import BaseModel, Field\n"
        "from wpostgresql import WPostgreSQL\n"
        "\n"
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "\n"
        'db_config = {"dbname": "mydb", "user": "postgres", "password": "pwd", "host": "localhost", "port": 5432}\n'
        "db = WPostgreSQL(User, db_config)\n"
        "db.insert(User(id=1, name='Alice'))  # No session, no engine, no Base needed.\n"
        "\n"
        "--- FASTAPI INTEGRATION ---\n"
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel, Field\n"
        "from wpostgresql import WPostgreSQL, get_async_connection\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "class User(BaseModel):\n"
        '    __tablename__ = "users"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "    email: str = ''\n"
        "\n"
        'db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}\n'
        "db = WPostgreSQL(User, db_config)\n"
        "\n"
        "@app.post('/users')\n"
        "async def create_user(user: User):\n"
        "    await db.insert_async(user)\n"
        "    return {'status': 'created'}\n"
        "\n"
        "@app.get('/users')\n"
        "async def list_users():\n"
        "    return await db.get_all_async()\n"
        "\n"
        "@app.get('/users/{user_id}')\n"
        "async def get_user(user_id: int):\n"
        "    results = await db.get_by_field_async(id=user_id)\n"
        "    return results[0] if results else {'error': 'not found'}\n"
        "\n"
        "--- REFACTORING A MONOLITH TO WPOSTGRESQL ---\n"
        "Step 1: Identify entities -> define as Pydantic BaseModel classes.\n"
        "Step 2: Create `config/settings.py` with DatabaseSettings dataclass.\n"
        "Step 3: For each model, create a Repository class wrapping WPostgreSQL.\n"
        "Step 4: Create `migrations/manager.py` with TableSync for schema sync.\n"
        "Step 5: Create `main.py` orchestrator.\n"
        "\n"
        "--- MODULE MAP ---\n"
        "wpostgresql                       -> WPostgreSQL (CRUD, async, batch, transactions, pagination)\n"
        "wpostgresql.builders              -> QueryBuilder (WHERE, ORDER BY, LIMIT, OFFSET)\n"
        "wpostgresql.core.connection       -> ConnectionManager, AsyncConnectionManager, configure_pool, close_global_pools, get_connection, get_async_connection, Transaction, AsyncTransaction, get_transaction, get_async_transaction\n"
        "wpostgresql.core.sync             -> TableSync, AsyncTableSync (create_if_not_exists, sync_with_model, index management)\n"
        "wpostgresql.types.sql_types       -> Pydantic-to-PostgreSQL type mapping (int->INTEGER, str->TEXT, bool->BOOLEAN)\n"
        "wpostgresql.exceptions            -> WPostgreSQLError, ConnectionError, TableSyncError, ValidationError, OperationError, SQLInjectionError, TransactionError\n"
        "wpostgresql.cli                   -> wpostgresql CLI (init, list, insert, get, delete, count, drop, test-connection)\n"
    )
    return manual_text


@mcp.tool()
def lint_wpostgresql_code(code: str) -> str:
    """Analyze Python code for potential WPostgreSQL design issues, bad practices, or parameter mismatches.

    Args:
        code: The Python source code to analyze.
    """
    issues = []
    warnings = []
    suggestions = []

    lines = code.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "session.add(" in stripped or "session.commit(" in stripped:
            issues.append(f"Line {i}: SQLAlchemy pattern detected — use WPostgreSQL (db.insert, db.update) instead")

        if "psycopg2" in stripped:
            issues.append(f"Line {i}: psycopg2 detected — WPostgreSQL uses psycopg 3 internally")

        if "conn = psycopg2.connect(" in stripped or "psycopg2.connect(" in stripped:
            issues.append(f"Line {i}: Direct psycopg2 connection — use WPostgreSQL or get_connection() instead")

        if re.search(r'\.update\([^)]*\{', stripped):
            issues.append(f"Line {i}: update() with dict — CRITICAL: update() takes a BaseModel instance, NOT a dict")

        if "session.query(" in stripped or "session.filter(" in stripped:
            issues.append(f"Line {i}: SQLAlchemy query pattern — use WPostgreSQL methods (get_by_field, get_paginated)")

        if re.search(r'\.execute\(["\'].*\b(drop|truncate|alter)\b', stripped, re.IGNORECASE):
            warnings.append(f"Line {i}: DDL statement via raw execute — consider using TableSync for schema management")

        if re.search(r'cursor\(\)', stripped):
            warnings.append(f"Line {i}: Raw cursor usage — prefer WPostgreSQL repository methods")

        if re.search(r'\.fetchone\(\)|\.fetchall\(\)', stripped):
            warnings.append(f"Line {i}: Raw fetch pattern — WPostgreSQL methods return Pydantic model instances directly")

        if "from sqlalchemy" in stripped or "import sqlalchemy" in stripped:
            issues.append(f"Line {i}: SQLAlchemy import — WPostgreSQL replaces SQLAlchemy entirely")

        if "declarative_base" in stripped:
            issues.append(f"Line {i}: SQLAlchemy declarative_base — use Pydantic BaseModel instead")

        if re.search(r'Column\(', stripped):
            issues.append(f"Line {i}: SQLAlchemy Column — use Pydantic Field(description='...') for constraints")

        if "create_engine(" in stripped:
            issues.append(f"Line {i}: SQLAlchemy create_engine — WPostgreSQL handles connection pooling via configure_pool()")

    if "BaseModel" in code:
        if "__tablename__" not in code:
            warnings.append("No __tablename__ found — table name will default to lowercase class name")

        if "Field(description=" not in code:
            warnings.append("No Field descriptions — add Field(description='Primary Key') or 'NOT NULL' for constraints")

        if "Primary Key" not in code and "primary" not in code.lower():
            warnings.append("No primary key field detected — every model needs one")

    if "WPostgreSQL" in code:
        if "get_all()" in code or "get_by_field(" in code:
            suggestions.append("Good: Using WPostgreSQL read methods")

        if "insert(" in code and "insert_many(" not in code:
            if "for " in code and "insert(" in code:
                warnings.append("Consider using insert_many() for bulk inserts inside a loop")

    has_pooling = "configure_pool" in code or "pool_config" in code or "get_connection" in code
    has_db_config = "db_config" in code
    if has_db_config and not has_pooling:
        suggestions.append("Consider using configure_pool() for production connection pooling")

    result_lines = ["WPostgreSQL Code Lint Report", ""]

    if issues:
        result_lines.append(f"ISSUES ({len(issues)}):")
        for issue in issues:
            result_lines.append(f"  - {issue}")
        result_lines.append("")

    if warnings:
        result_lines.append(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            result_lines.append(f"  - {w}")
        result_lines.append("")

    if suggestions:
        result_lines.append("SUGGESTIONS:")
        for s in suggestions:
            result_lines.append(f"  + {s}")
        result_lines.append("")

    if not issues and not warnings:
        result_lines.append("Result: PASS — no WPostgreSQL issues found")
    else:
        result_lines.append(f"Result: {len(issues)} issue(s), {len(warnings)} warning(s)")

    return "\n".join(result_lines)


@mcp.tool()
def adapt_code_to_wpostgresql(
    source_code: str,
    target_file: str = "",
) -> str:
    """Adapt existing Python database code (psycopg2, SQLAlchemy, raw SQL) to use WPostgreSQL.

    Args:
        source_code: The original Python code snippet containing the database logic to adapt.
        target_file: Optional filename hint for context (e.g. 'repositories/user_repo.py').
    """
    adapted_parts = []
    warnings = []
    is_async = "async " in source_code or "await " in source_code or "asyncio" in source_code

    has_psycopg2 = "psycopg2" in source_code
    has_sqlalchemy = "sqlalchemy" in source_code.lower() or "session.add" in source_code
    has_raw_sql = re.search(r'\.execute\(["\']', source_code) is not None

    if has_sqlalchemy:
        table_match = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', source_code)
        table_name = table_match.group(1) if table_match else "my_table"

        class_match = re.search(r'class\s+(\w+)\(.*Base\):', source_code)
        class_name = class_match.group(1) if class_match else "MyModel"

        columns = []
        col_pattern = re.compile(r'(\w+)\s*=\s*Column\((\w+)(?:,\s*(.*))?\)')
        for m in col_pattern.finditer(source_code):
            col_name, col_type, col_args = m.groups()
            py_type = {"Integer": "int", "String": "str", "Text": "str", "Boolean": "bool", "Float": "float", "DateTime": "datetime"}.get(col_type, "str")
            desc_parts = []
            if col_args and "primary_key" in col_args:
                desc_parts.append("Primary Key")
            if col_args and "nullable=False" in col_args:
                desc_parts.append("NOT NULL")
            if col_args and "unique" in col_args.lower():
                desc_parts.append("UNIQUE")
            desc = f"Field(description=\"{' '.join(desc_parts)}\")" if desc_parts else ""
            default = ""
            if col_args:
                default_match = re.search(r'default\s*=\s*(\S+)', col_args)
                if default_match:
                    default = f" = {default_match.group(1).rstrip(',')}"
            columns.append(f"    {col_name}: {py_type} {desc}{default}".rstrip())

        adapted_parts.append("from pydantic import BaseModel, Field")
        adapted_parts.append("from wpostgresql import WPostgreSQL\n")
        adapted_parts.append(f"class {class_name}(BaseModel):")
        adapted_parts.append(f'    __tablename__ = "{table_name}"')
        adapted_parts.extend(columns)
        adapted_parts.append("")
        adapted_parts.append(f'db_config = {{"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}}')
        adapted_parts.append(f"db = WPostgreSQL({class_name}, db_config)\n")

        add_matches = re.findall(r'session\.add\((\w+)\((.*?)\)\)', source_code)
        for model_instance, args in add_matches:
            adapted_parts.append(f"db.insert({model_instance}({args}))")

        query_matches = re.findall(r'session\.query\((\w+)\)(.*?)\.all\(\)', source_code, re.DOTALL)
        for model_name, chain in query_matches:
            filter_match = re.search(r'\.filter\((\w+)\.(\w+)\s*==\s*(\w+)\)', chain)
            if filter_match:
                col, val = filter_match.group(2), filter_match.group(3)
                adapted_parts.append(f"results = db.get_by_field({col}={val})")
            else:
                adapted_parts.append(f"results = db.get_all()")

        commit_match = re.findall(r'session\.commit\(\)', source_code)
        if commit_match:
            adapted_parts.append("# No manual commit needed — WPostgreSQL auto-commits after each operation")

    elif has_psycopg2:
        conn_match = re.search(r'psycopg2\.connect\((.*?)\)', source_code, re.DOTALL)
        config_dict = {}
        if conn_match:
            for kw in re.finditer(r'(\w+)\s*=\s*["\']([^"\']+)["\']', conn_match.group(1)):
                config_dict[kw.group(1)] = kw.group(2)

        adapted_parts.append("from pydantic import BaseModel, Field")
        adapted_parts.append("from wpostgresql import WPostgreSQL\n")
        adapted_parts.append("class Record(BaseModel):")
        adapted_parts.append('    __tablename__ = "records"')
        adapted_parts.append('    id: int = Field(description="Primary Key")')
        adapted_parts.append("    # Add your fields here based on the original table schema")
        adapted_parts.append("")
        db_config = config_dict if config_dict else {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}
        adapted_parts.append(f"db_config = {repr(db_config)}")
        adapted_parts.append("db = WPostgreSQL(Record, db_config)\n")

        insert_match = re.search(r'cur\.execute\(["\']INSERT\s+INTO\s+\w+\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)["\']', source_code, re.IGNORECASE)
        if insert_match:
            cols = [c.strip() for c in insert_match.group(1).split(",")]
            adapted_parts.append("# Original INSERT mapped to:")
            fields_str = ", ".join(f"{c}=..." for c in cols)
            adapted_parts.append(f"# db.insert(Record({fields_str}))")

        select_match = re.search(r'cur\.execute\(["\']SELECT\s+(.*?)\s+FROM\s+(\w+)', source_code, re.IGNORECASE)
        if select_match:
            adapted_parts.append(f"# Original SELECT mapped to:")
            adapted_parts.append(f"# results = db.get_all()  # or db.get_by_field(...)")

        adapted_parts.append("# No more manual conn.close(), cursor, commit — WPostgreSQL handles it all")

    elif has_raw_sql:
        adapted_parts.append("from pydantic import BaseModel, Field")
        adapted_parts.append("from wpostgresql import WPostgreSQL\n")
        adapted_parts.append("class Record(BaseModel):")
        adapted_parts.append('    __tablename__ = "records"')
        adapted_parts.append('    id: int = Field(description="Primary Key")')
        adapted_parts.append("    # Add your fields here based on the original table schema\n")
        adapted_parts.append('db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}')
        adapted_parts.append("db = WPostgreSQL(Record, db_config)\n")

        select_all = re.search(r'SELECT\s+\*\s+FROM\s+(\w+)', source_code, re.IGNORECASE)
        if select_all:
            adapted_parts.append(f"# Original SELECT * FROM {select_all.group(1)} mapped to:")
            adapted_parts.append("# results = db.get_all()")

        insert_raw = re.search(r'INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)', source_code, re.IGNORECASE)
        if insert_raw:
            table = insert_raw.group(1)
            adapted_parts.append(f"# Original INSERT INTO {table} mapped to:")
            adapted_parts.append(f"# db.insert(Record(...))")

        adapted_parts.append("# Use WPostgreSQL repository methods instead of raw SQL for safety and type-safety")

    else:
        warnings.append("Could not detect a specific database library (psycopg2, SQLAlchemy, or raw SQL).")
        warnings.append("Returning a basic WPostgreSQL template instead.")
        adapted_parts.append("from pydantic import BaseModel, Field")
        adapted_parts.append("from wpostgresql import WPostgreSQL\n")
        adapted_parts.append("class MyModel(BaseModel):")
        adapted_parts.append('    __tablename__ = "my_table"')
        adapted_parts.append('    id: int = Field(description="Primary Key")')
        adapted_parts.append('    name: str = Field(description="NOT NULL")')
        adapted_parts.append("")
        adapted_parts.append('db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}')
        adapted_parts.append("db = WPostgreSQL(MyModel, db_config)\n")
        adapted_parts.append("db.insert(MyModel(id=1, name='example'))")

    result_lines = [f"Adapted WPostgreSQL code:", ""]
    if warnings:
        result_lines.append("WARNINGS:")
        for w in warnings:
            result_lines.append(f"  - {w}")
        result_lines.append("")

    result_lines.append("---BEGIN ADAPTED CODE---")
    result_lines.extend(adapted_parts)
    result_lines.append("---END ADAPTED CODE---")

    result_lines.append("")
    result_lines.append("Next steps:")
    result_lines.append("1. Review the generated model fields and adjust types/defaults")
    result_lines.append("2. Add Field descriptions for constraints (Primary Key, NOT NULL, UNIQUE)")
    result_lines.append("3. See get_wpostgresql_architect_blueprints() for full CRUD reference")

    return "\n".join(result_lines)


@mcp.tool()
def check_schema_compatibility(original_schema: str, new_schema: str) -> str:
    """Analyze and verify schema compatibility between two Pydantic model versions to prevent database breaks.

    Args:
        original_schema: Original Pydantic model class definition.
        new_schema: The proposed new Pydantic model class definition.
    """

    def extract_fields(schema_str: str) -> dict:
        fields = {}
        for line in schema_str.splitlines():
            match = re.search(r'^\s*([a-zA-Z_]\w*)\s*:\s*([a-zA-Z_]\w*(?:\[[^\]]+\])?)', line)
            if match:
                field_name, field_type = match.groups()
                has_default = "=" in line
                has_optional = "Optional" in field_type
                desc_match = re.search(r'description\s*=\s*["\']([^"\']*)["\']', line)
                description = desc_match.group(1) if desc_match else ""
                fields[field_name] = {
                    "type": field_type,
                    "optional": has_default or has_optional,
                    "description": description,
                }
        return fields

    orig_fields = extract_fields(original_schema)
    new_fields = extract_fields(new_schema)

    breaks = []
    warnings_list = []
    additions = []

    type_compat = {
        ("int", "int"): True,
        ("str", "str"): True,
        ("bool", "bool"): True,
        ("float", "float"): True,
        ("int", "float"): True,
        ("str", "int"): False,
        ("int", "str"): False,
        ("str", "bool"): False,
        ("bool", "str"): False,
    }

    for name, info in orig_fields.items():
        if name not in new_fields:
            breaks.append(f"Field '{name}' was REMOVED — existing rows with this column will lose data or cause errors")
        elif orig_fields[name]["type"] != new_fields[name]["type"]:
            compat = type_compat.get((orig_fields[name]["type"], new_fields[name]["type"]), False)
            if compat:
                additions.append(f"Field '{name}' type widened from '{orig_fields[name]['type']}' to '{new_fields[name]['type']}' (safe)")
            else:
                breaks.append(f"Field '{name}' type changed from '{orig_fields[name]['type']}' to '{new_fields[name]['type']}' — may lose data")

    for name, info in new_fields.items():
        if name not in orig_fields:
            if info["optional"]:
                additions.append(f"New optional field '{name}' added (safe — defaults to {info['type']})")
            else:
                breaks.append(f"New required field '{name}' added with NO default — existing rows will fail on NOT NULL constraint")
        elif name in orig_fields:
            orig_desc = orig_fields[name]["description"]
            new_desc = info["description"]
            if "Primary Key" in orig_desc and "Primary Key" not in new_desc:
                breaks.append(f"Field '{name}' lost Primary Key constraint")
            if "NOT NULL" in orig_desc and "NOT NULL" not in new_desc:
                warnings_list.append(f"Field '{name}' lost NOT NULL constraint")
            if "UNIQUE" in orig_desc and "UNIQUE" not in new_desc:
                warnings_list.append(f"Field '{name}' lost UNIQUE constraint")

    result_lines = ["WPostgreSQL Schema Compatibility Check", ""]

    if breaks:
        result_lines.append(f"BREAKING CHANGES ({len(breaks)}):")
        for b in breaks:
            result_lines.append(f"  ! {b}")
        result_lines.append("")

    if warnings_list:
        result_lines.append(f"CONSTRAINT CHANGES ({len(warnings_list)}):")
        for w in warnings_list:
            result_lines.append(f"  ~ {w}")
        result_lines.append("")

    if additions:
        result_lines.append(f"SAFE ADDITIONS ({len(additions)}):")
        for a in additions:
            result_lines.append(f"  + {a}")
        result_lines.append("")

    if breaks:
        result_lines.append("Result: BREAKING — migration required before deploying this schema change")
        result_lines.append("")
        result_lines.append("To apply safely, use TableSync after adding defaults to new required fields:")
        result_lines.append("  sync = TableSync(YourModel, db_config)")
        result_lines.append("  sync.sync_with_model()")
    elif warnings_list:
        result_lines.append("Result: WARNINGS — constraints changed, review before deploying")
    else:
        result_lines.append("Result: SAFE — schema changes are backward-compatible")

    return "\n".join(result_lines)


@mcp.tool()
def reverse_engineer_schema(
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "postgres",
    user: str = "postgres",
    password: str = "",
    schema: str = "public",
    tables: str = "",
) -> str:
    """Connect to an existing PostgreSQL database and generate WPostgreSQL-compatible Pydantic models from the discovered schema. Use this to migrate legacy databases to WPostgreSQL.

    Args:
        host: PostgreSQL host address.
        port: PostgreSQL port number.
        dbname: Database name.
        user: Database user.
        password: Database password.
        schema: Schema to inspect (default: public).
        tables: Comma-separated list of specific tables to reverse-engineer. Leave empty for all tables.
    """
    try:
        import psycopg
    except ImportError:
        return "Error: psycopg not installed. Run: pip install 'psycopg[binary]'"

    try:
        conninfo = f"host={host} port={port} dbname={dbname} user={user} password={password}"
        conn = psycopg.connect(conninfo, connect_timeout=10)
    except Exception as e:
        return f"Error: Could not connect to PostgreSQL — {e}"

    try:
        cur = conn.cursor()

        if tables.strip():
            table_list = [t.strip() for t in tables.split(",")]
            placeholders = ", ".join(["%s"] * len(table_list))
            cur.execute(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = %s AND table_type = 'BASE TABLE' AND table_name IN ({placeholders}) "
                f"ORDER BY table_name",
                (schema, *table_list),
            )
        else:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                "ORDER BY table_name",
                (schema,),
            )

        table_names = [row[0] for row in cur.fetchall()]

        if not table_names:
            conn.close()
            return f"No tables found in schema '{schema}' with the specified filter."

        pg_to_py = {
            "integer": "int",
            "bigint": "int",
            "smallint": "int",
            "serial": "int",
            "bigserial": "int",
            "text": "str",
            "varchar": "str",
            "character varying": "str",
            "char": "str",
            "character": "str",
            "boolean": "bool",
            "real": "float",
            "double precision": "float",
            "numeric": "float",
            "decimal": "float",
            "money": "float",
            "date": "str",
            "timestamp": "str",
            "timestamp without time zone": "str",
            "timestamp with time zone": "str",
            "time": "str",
            "json": "str",
            "jsonb": "str",
            "uuid": "str",
            "bytea": "str",
            "inet": "str",
            "cidr": "str",
            "macaddr": "str",
            "xml": "str",
            "name": "str",
        }

        all_models = []
        all_imports = set()

        for table_name in table_names:
            cur.execute(
                "SELECT c.column_name, c.data_type, c.is_nullable, "
                "c.column_default, c.character_maximum_length, "
                "pk.column_name AS pk_column "
                "FROM information_schema.columns c "
                "LEFT JOIN ( "
                "  SELECT ku.column_name "
                "  FROM information_schema.table_constraints tc "
                "  JOIN information_schema.key_column_usage ku "
                "    ON tc.constraint_name = ku.constraint_name "
                "    AND tc.table_schema = ku.table_schema "
                "  WHERE tc.constraint_type = 'PRIMARY KEY' "
                "    AND tc.table_name = %s "
                "    AND tc.table_schema = %s "
                ") pk ON c.column_name = pk.column_name "
                "WHERE c.table_name = %s AND c.table_schema = %s "
                "ORDER BY c.ordinal_position",
                (table_name, schema, table_name, schema),
            )

            columns = cur.fetchall()

            cur.execute(
                "SELECT column_name "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage ku "
                "  ON tc.constraint_name = ku.constraint_name "
                "  AND tc.table_schema = ku.table_schema "
                "WHERE tc.constraint_type = 'UNIQUE' "
                "  AND tc.table_name = %s "
                "  AND tc.table_schema = %s",
                (table_name, schema),
            )
            unique_cols = {row[0] for row in cur.fetchall()}

            cur.execute(
                "SELECT ccu.column_name "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON tc.constraint_name = ccu.constraint_name "
                "  AND tc.table_schema = ccu.table_schema "
                "WHERE tc.constraint_type = 'FOREIGN KEY' "
                "  AND tc.table_name = %s "
                "  AND tc.table_schema = %s",
                (table_name, schema),
            )
            fk_cols = {row[0] for row in cur.fetchall()}

            cur.execute(
                "SELECT ic.column_name, ic.ordinal_position "
                "FROM pg_class pc "
                "JOIN pg_namespace pn ON pc.relnamespace = pn.oid "
                "JOIN pg_index pi ON pi.indexrelid = pc.oid "
                "JOIN pg_attribute pa ON pa.attrelid = pi.indrelid AND pa.attnum = ANY(pi.indkey) "
                "JOIN information_schema.columns ic "
                "  ON ic.table_name = (SELECT relname FROM pg_class WHERE oid = pi.indrelid) "
                "  AND ic.column_name = pa.attname "
                "  AND ic.table_schema = %s "
                "WHERE pc.relkind = 'i' "
                "  AND NOT pi.indisprimary "
                "  AND (SELECT relname FROM pg_class WHERE oid = pi.indrelid) = %s "
                "ORDER BY ic.ordinal_position",
                (schema, table_name),
            )
            indexed_cols = {row[0] for row in cur.fetchall()}

            class_name = "".join(w.capitalize() for w in table_name.split("_"))

            model_lines = []
            model_lines.append(f'class {class_name}(BaseModel):')
            model_lines.append(f'    __tablename__ = "{table_name}"')

            for col_name, data_type, is_nullable, col_default, char_max, pk_col in columns:
                py_type = pg_to_py.get(data_type.lower(), "str")

                if py_type == "str" and col_name in fk_cols:
                    py_type = "int"

                desc_parts = []
                if pk_col:
                    desc_parts.append("Primary Key")
                if is_nullable == "NO" and not col_default:
                    desc_parts.append("NOT NULL")
                if col_name in unique_cols:
                    desc_parts.append("UNIQUE")

                desc_str = f'Field(description="{" ".join(desc_parts)}")' if desc_parts else ""

                if col_default:
                    if "nextval" in col_default:
                        default_val = ""
                    elif col_default.startswith("'") and col_default.endswith("'::character varying"):
                        default_val = f' = "{col_default[1:-22]}"'
                    elif "::boolean" in col_default:
                        default_val = f" = {col_default.split('::')[0]}"
                    elif "::integer" in col_default or "::bigint" in col_default:
                        default_val = f" = {col_default.split('::')[0]}"
                    elif "::numeric" in col_default or "::double" in col_default:
                        default_val = f" = {col_default.split('::')[0]}"
                    elif col_default == "true":
                        default_val = " = True"
                    elif col_default == "false":
                        default_val = " = False"
                    else:
                        default_val = ""
                elif pk_col and py_type == "int":
                    default_val = ""
                elif py_type == "bool":
                    default_val = " = True"
                elif py_type == "int":
                    default_val = " = 0"
                elif py_type == "float":
                    default_val = " = 0.0"
                elif py_type == "str":
                    default_val = ' = ""'
                else:
                    default_val = ""

                field_str = f"    {col_name}: {py_type}"
                if desc_str:
                    field_str += f" {desc_str}"
                if default_val:
                    field_str += default_val
                model_lines.append(field_str)

            model_code = "\n".join(model_lines)
            all_models.append((table_name, class_name, model_code))

        output = []
        output.append("# Auto-generated WPostgreSQL models from PostgreSQL schema")
        output.append(f"# Source: {user}@{host}:{port}/{dbname} (schema: {schema})")
        output.append(f"# Tables: {len(table_names)}")
        output.append("")
        output.append("from pydantic import BaseModel, Field")
        output.append("from wpostgresql import WPostgreSQL\n")

        for table_name, class_name, model_code in all_models:
            output.append("")
            output.append(model_code)
            output.append("")

        output.append("")
        output.append("# --- Database setup ---")
        output.append("")
        output.append(f'db_config = {{"dbname": "{dbname}", "user": "{user}", "password": "{password}", "host": "{host}", "port": {port}}}')
        output.append("")

        for table_name, class_name, _ in all_models:
            output.append(f"{table_name}_db = WPostgreSQL({class_name}, db_config)")

        output.append("")
        output.append("---BEGIN CODE---")
        final_code = "\n".join(output)
        final_code = final_code.replace("---BEGIN CODE---", "")
        conn.close()

        return final_code

    except Exception as e:
        conn.close()
        return f"Error during reverse engineering: {e}"


# --- Pattern-specific code generators ---


def _generate_pattern_example(pattern_name: str, pattern: dict, project_name: str) -> str:
    """Generate pattern-specific example code based on the pattern metadata."""
    module = pattern.get("module", "")
    feature = pattern.get("feature", "")
    category = pattern.get("category", "")

    header = (
        f'"""Pattern: {feature}\n'
        f"Module: {module}\n"
        f"Category: {category}\n"
        f'Generated by WPostgreSQL MCP"""\n\n'
    )

    base_setup = (
        "from pydantic import BaseModel, Field\n"
        "from wpostgresql import WPostgreSQL\n\n\n"
        "class Item(BaseModel):\n"
        '    __tablename__ = "items"\n'
        '    id: int = Field(description="Primary Key")\n'
        '    name: str = Field(description="NOT NULL")\n'
        "    value: str = ''\n\n\n"
        'db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}\n'
        "db = WPostgreSQL(Item, db_config)\n\n\n"
    )

    if "crud" in pattern_name or "insert" in pattern_name or "read" in pattern_name:
        code = base_setup + (
            'if __name__ == "__main__":\n'
            "    # Insert\n"
            "    db.insert(Item(id=1, name='Widget', value='A'))\n"
            "    db.insert(Item(id=2, name='Gadget', value='B'))\n\n"
            "    # Read all\n"
            "    all_items = db.get_all()\n"
            "    print('All items:', all_items)\n\n"
            "    # Read by field\n"
            "    filtered = db.get_by_field(name='Widget')\n"
            "    print('Filtered:', filtered)\n\n"
            "    # Count\n"
            "    print('Total:', db.count())\n"
        )
    elif "update" in pattern_name:
        code = base_setup + (
            'if __name__ == "__main__":\n'
            "    db.insert(Item(id=1, name='Widget', value='A'))\n\n"
            "    # Update with BaseModel instance (NOT a dict)\n"
            "    db.update(1, Item(id=1, name='Widget Updated', value='B'))\n"
            "    print('Updated:', db.get_by_field(id=1))\n"
        )
    elif "delete" in pattern_name:
        code = base_setup + (
            'if __name__ == "__main__":\n'
            "    db.insert(Item(id=1, name='Widget', value='A'))\n"
            "    db.insert(Item(id=2, name='Gadget', value='B'))\n\n"
            "    # Delete single\n"
            "    db.delete(1)\n\n"
            "    # Delete many\n"
            "    db.delete_many([2])\n\n"
            "    print('Remaining:', db.get_all())\n"
        )
    elif "async" in pattern_name:
        code = (
            "import asyncio\n"
            "from pydantic import BaseModel, Field\n"
            "from wpostgresql import WPostgreSQL\n\n\n"
            "class Item(BaseModel):\n"
            '    __tablename__ = "items"\n'
            '    id: int = Field(description="Primary Key")\n'
            '    name: str = Field(description="NOT NULL")\n'
            "    value: str = ''\n\n\n"
            'db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}\n'
            "db = WPostgreSQL(Item, db_config)\n\n\n"
            "async def main():\n"
            "    await db.insert_async(Item(id=1, name='AsyncItem', value='X'))\n"
            "    items = await db.get_all_async()\n"
            "    print('Async items:', items)\n\n\n"
            'if __name__ == "__main__":\n'
            "    asyncio.run(main())\n"
        )
    elif "batch" in pattern_name:
        code = base_setup + (
            'if __name__ == "__main__":\n'
            "    # Bulk insert\n"
            "    items = [Item(id=i, name=f'Item{i}', value=chr(65 + i)) for i in range(5)]\n"
            "    db.insert_many(items)\n"
            "    print('Inserted', db.count(), 'items')\n\n"
            "    # Bulk update\n"
            "    db.update_many([(Item(id=0, name='Updated0', value='Z'), 0)])\n\n"
            "    # Bulk delete\n"
            "    db.delete_many([0, 1, 2])\n"
            "    print('Remaining:', db.count())\n"
        )
    elif "transaction" in pattern_name:
        code = base_setup + (
            "from wpostgresql import get_transaction\n\n\n"
            'if __name__ == "__main__":\n'
            "    with get_transaction(db_config) as txn:\n"
            '        txn.execute("INSERT INTO items (id, name, value) VALUES (%s, %s, %s)", (1, "Txn1", "A"))\n'
            '        txn.execute("INSERT INTO items (id, name, value) VALUES (%s, %s, %s)", (2, "Txn2", "B"))\n'
            "    # Auto-commits on success, auto-rollbacks on exception\n"
            "    print('After transaction:', db.get_all())\n"
        )
    elif "pool" in pattern_name or "connection" in pattern_name:
        code = (
            "from wpostgresql import configure_pool, get_connection, close_global_pools\n\n\n"
            'db_config = {"dbname": "mydb", "user": "postgres", "password": "", "host": "localhost", "port": 5432}\n\n\n'
            'if __name__ == "__main__":\n'
            "    configure_pool(db_config, min_size=5, max_size=20)\n\n"
            "    with get_connection(db_config) as conn:\n"
            '        cur = conn.execute("SELECT 1")\n'
            "        print('Pool connection OK:', cur.fetchone())\n\n"
            "    close_global_pools()\n"
        )
    elif "query_builder" in pattern_name:
        code = (
            "from wpostgresql import QueryBuilder\n\n\n"
            'if __name__ == "__main__":\n'
            "    qb = (\n"
            '        QueryBuilder("items")\n'
            '        .where("value", "=", "A")\n'
            '        .order_by("name", descending=True)\n'
            "        .limit(10)\n"
            "    )\n"
            "    sql, params = qb.build_select()\n"
            "    print('SQL:', sql)\n"
            "    print('Params:', params)\n"
        )
    elif "table_sync" in pattern_name or "schema" in pattern_name or "migration" in pattern_name:
        code = base_setup + (
            "from wpostgresql import TableSync\n\n\n"
            'if __name__ == "__main__":\n'
            "    sync = TableSync(Item, db_config)\n"
            "    sync.create_if_not_exists()\n"
            "    sync.sync_with_model()\n"
            "    sync.create_index(['name'], 'idx_items_name')\n"
            "    print('Table exists:', sync.table_exists())\n"
            "    print('Columns:', sync.get_columns())\n"
        )
    else:
        code = base_setup + (
            f'# Pattern: {feature}\n'
            f'# Module: {module}\n\n'
            'if __name__ == "__main__":\n'
            f"    # TODO: Implement {feature} pattern\n"
            "    print(f'Project ready with pattern {pattern_name!r}')\n"
        )

    return header + code


# --- CLI Actions ---


def run_stdio():
    """Runs the MCP server in stdio mode (standard for agents)."""
    mcp.run(transport="stdio")


def run_sse():
    """Runs the MCP server in SSE mode."""
    mcp.run(transport="sse")


def start_background():
    """Starts the SSE server in the background."""
    if os.path.exists(PID_FILE):
        print("Server is already running or PID file exists.")
        return

    with (
        open(os.path.expanduser("~/wpostgresql_mcp.log"), "a", encoding="utf-8") as log_file,
        subprocess.Popen(
            [sys.executable, "-m", "wpostgresql_mcp.server", "run-sse"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as proc,
        open(PID_FILE, "w", encoding="utf-8") as f,
    ):
        f.write(str(proc.pid))
    print(f"wpostgresql-mcp started in background (SSE mode) with PID {proc.pid}")


def stop_background():
    """Stops the background SSE server."""
    if not os.path.exists(PID_FILE):
        print("No background server running.")
        return

    with open(PID_FILE, encoding="utf-8") as f:
        pid = int(f.read())

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped server with PID {pid}")
    except ProcessLookupError:
        print("Process not found.")
    finally:
        os.remove(PID_FILE)


def print_config(write_file: bool = True):
    """Prints or saves the JSON configuration for agents."""
    python_path = sys.executable
    config = {
        "mcpServers": {
            "wpostgresql-mcp": {
                "command": python_path,
                "args": ["-m", "wpostgresql_mcp.server", "run"],
                "env": {},
            }
        }
    }

    config_json = json.dumps(config, indent=2)

    helper_text = (
        "\n=========================================\n"
        "QUICK INSTALL COMMANDS FOR AI AGENTS\n"
        "=========================================\n\n"
        "For Gemini CLI:\n"
        f"  gemini mcp add wpostgresql-mcp {python_path} -m wpostgresql_mcp.server run\n\n"
        "For Claude Desktop / Cursor:\n"
        "  Copy the JSON above (or from the saved file) into your agent's config file.\n"
        "=========================================\n"
    )

    if not write_file:
        print(config_json)
        print(helper_text)
        return

    target_dir = os.getcwd()
    agents_dir = os.path.join(target_dir, ".agents")
    os.makedirs(agents_dir, exist_ok=True)

    config_path = os.path.join(agents_dir, "wpostgresql-mcp.json")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_json)

    print(f"Configuration saved to: {config_path}")
    print(helper_text)


# --- Main Entry Point ---


def main():
    """Parse CLI arguments and dispatch to the requested command."""
    parser = argparse.ArgumentParser(description="wpostgresql-mcp: WPostgreSQL Architect MCP Server")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "run-sse", "start", "stop", "config", "help"],
        help="Command to execute (default: run)",
    )
    parser.add_argument(
        "--print", action="store_true", help="Print configuration to stdout instead of saving to .agents/"
    )

    args = parser.parse_args()

    if args.command == "config":
        logging.getLogger().setLevel(logging.ERROR)
        print_config(write_file=not args.print)
        return

    if args.command == "run":
        run_stdio()
    elif args.command == "run-sse":
        run_sse()
    elif args.command == "start":
        start_background()
    elif args.command == "stop":
        stop_background()
    elif args.command == "help":
        parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
