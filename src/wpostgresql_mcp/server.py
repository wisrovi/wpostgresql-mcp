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
    """Generate pytest unit tests for all repository classes in a WPostgreSQL project."""
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

        # Read the repo file to detect method names
        repo_path = os.path.join(repos_dir, repo_file)
        with open(repo_path, encoding="utf-8") as f:
            repo_content = f.read()

        methods = re.findall(r"def (\w+)\(self", repo_content)

        test_content = f'"""Auto-generated tests for {class_name}."""\n\n'
        test_content += "from unittest import mock\n\nimport pytest\n\n"
        test_content += f"from models.{model_name} import {model_class}\n"
        test_content += f"from repositories.{repo_name} import {class_name}\n"
        test_content += "from config.settings import DatabaseSettings\n\n\n"
        test_content += "@pytest.fixture\ndef settings():\n"
        test_content += '    return DatabaseSettings(dbname="testdb", user="test", password="test", host="localhost")\n\n\n'
        test_content += f"@pytest.fixture\ndef repo(settings):\n"
        test_content += f"    with mock.patch('repositories.{repo_name}.WPostgreSQL') as MockDB:\n"
        test_content += "        instance = MockDB.return_value\n"
        test_content += f"        yield {class_name}(settings), instance\n\n\n"

        for method in methods:
            if method.startswith("_"):
                continue
            test_name = f"test_{method}"
            if "create" in method or "insert" in method:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}({model_class}(id=1, name='test'))\n"
                test_content += f"    db.insert.assert_called_once()\n\n"
            elif "get_all" in method:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.get_all.return_value = [{model_class}(id=1, name='test')]\n"
                test_content += f"    result = r.{method}()\n"
                test_content += f"    assert isinstance(result, list)\n\n"
            elif "delete" in method:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}(1)\n"
                test_content += f"    db.delete.assert_called_once_with(1)\n\n"
            elif "count" in method:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    db.count.return_value = 42\n"
                test_content += f"    assert r.{method}() == 42\n\n"
            elif "update" in method:
                test_content += f"def {test_name}(repo):\n"
                test_content += f"    r, db = repo\n"
                test_content += f"    r.{method}(1, {model_class}(id=1, name='updated'))\n"
                test_content += f"    db.update.assert_called_once()\n\n"
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
        f"Generated {len(generated)} test file(s):\n"
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
