"""Advanced scaffolding templates for professional WPostgreSQL development."""


class TemplateGenerator:
    """Provides professional boilerplate for WPostgreSQL projects following wisrovi standards."""

    @staticmethod
    def get_supported_types() -> list[str]:
        """Return the list of supported scaffold types."""
        return ["standard", "api_service"]

    @staticmethod
    def get_folders(scaffold_type: str) -> list[str]:
        """Return the folder layout for the requested scaffold type."""
        base = ["config", "models", "repositories", "migrations", "tests", ".wpostgresql"]
        if scaffold_type == "api_service":
            base.append("routes")
        return base

    @staticmethod
    def get_files_blueprint(scaffold_type: str, project_name: str = "wpostgresql_project") -> dict[str, str]:
        """Return filenames and their professional template content."""
        settings_template = (
            "from dataclasses import dataclass\n"
            "import os\n\n\n"
            "@dataclass\n"
            "class DatabaseSettings:\n"
            '    """Centralized connection settings for WPostgreSQL."""\n\n'
            '    dbname: str = "mydb"\n'
            '    user: str = "postgres"\n'
            '    password: str = ""\n'
            '    host: str = "localhost"\n'
            "    port: int = 5432\n"
            "    pool_min_size: int = 5\n"
            "    pool_max_size: int = 50\n\n"
            "    def to_dict(self) -> dict:\n"
            '        """Convert to db_config dict for WPostgreSQL."""\n'
            "        return {\n"
            '            "dbname": self.dbname,\n'
            '            "user": self.user,\n'
            '            "password": self.password,\n'
            '            "host": self.host,\n'
            '            "port": self.port,\n'
            "        }\n\n"
            "    @classmethod\n"
            '    def from_env(cls) -> "DatabaseSettings":\n'
            '        """Build settings from environment variables with sane defaults."""\n'
            "        return cls(\n"
            '            dbname=os.getenv("PG_DATABASE", "mydb"),\n'
            '            user=os.getenv("PG_USER", "postgres"),\n'
            '            password=os.getenv("PG_PASSWORD", ""),\n'
            '            host=os.getenv("PG_HOST", "localhost"),\n'
            '            port=int(os.getenv("PG_PORT", "5432")),\n'
            '            pool_min_size=int(os.getenv("PG_POOL_MIN", "5")),\n'
            '            pool_max_size=int(os.getenv("PG_POOL_MAX", "50")),\n'
            "        )\n"
        )

        user_model_template = (
            "from pydantic import BaseModel, Field\n\n\n"
            "class User(BaseModel):\n"
            '    """User entity with PostgreSQL constraints via Field descriptions."""\n\n'
            '    __tablename__ = "users"\n'
            '    id: int = Field(description="Primary Key")\n'
            '    name: str = Field(description="NOT NULL")\n'
            '    email: str = Field(default="", description="UNIQUE")\n'
            "    age: int = 0\n"
            "    is_active: bool = True\n"
        )

        post_model_template = (
            "from pydantic import BaseModel, Field\n\n\n"
            "class Post(BaseModel):\n"
            '    """Post entity with foreign key reference to User."""\n\n'
            '    __tablename__ = "posts"\n'
            '    id: int = Field(description="Primary Key")\n'
            '    user_id: int = Field(description="NOT NULL")\n'
            '    title: str = Field(description="NOT NULL")\n'
            '    content: str = ""\n'
        )

        user_repo_template = (
            "from wpostgresql import WPostgreSQL\n"
            "from models.user import User\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "class UserRepository:\n"
            '    """User data access layer."""\n\n'
            "    def __init__(self, settings: DatabaseSettings):\n"
            "        self.db = WPostgreSQL(\n"
            "            User,\n"
            "            settings.to_dict(),\n"
            "            pool_config={\n"
            '                "min_size": settings.pool_min_size,\n'
            '                "max_size": settings.pool_max_size,\n'
            "            },\n"
            "        )\n\n"
            "    def create(self, user: User) -> None:\n"
            '        """Insert a new user (returns None, use get_by_field to retrieve)."""\n'
            "        self.db.insert(user)\n\n"
            "    def get_all(self) -> list[User]:\n"
            '        """Get all users."""\n'
            "        return self.db.get_all()\n\n"
            "    def get_by_id(self, user_id: int) -> list[User]:\n"
            '        """Get user by ID."""\n'
            "        return self.db.get_by_field(id=user_id)\n\n"
            "    def get_by_email(self, email: str) -> list[User]:\n"
            '        """Get user by email."""\n'
            "        return self.db.get_by_field(email=email)\n\n"
            "    def get_paginated(self, page: int = 1, per_page: int = 20) -> list[User]:\n"
            '        """Get paginated users."""\n'
            "        return self.db.get_page(page=page, per_page=per_page)\n\n"
            "    def update(self, user_id: int, user: User) -> None:\n"
            '        """Update user by ID. Pass a User instance, not a dict."""\n'
            "        self.db.update(user_id, user)\n\n"
            "    def delete(self, user_id: int) -> None:\n"
            '        """Delete user by ID."""\n'
            "        self.db.delete(user_id)\n\n"
            "    def count(self) -> int:\n"
            '        """Count all users."""\n'
            "        return self.db.count()\n\n"
            "    # Async variants\n"
            "    async def create_async(self, user: User) -> None:\n"
            "        self.db.insert(user)\n\n"
            "    async def get_all_async(self) -> list[User]:\n"
            "        return await self.db.get_all_async()\n\n"
            "    async def get_by_id_async(self, user_id: int) -> list[User]:\n"
            "        return await self.db.get_by_field_async(id=user_id)\n\n"
            "    async def get_by_email_async(self, email: str) -> list[User]:\n"
            "        return await self.db.get_by_field_async(email=email)\n"
        )

        post_repo_template = (
            "from wpostgresql import WPostgreSQL\n"
            "from models.post import Post\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "class PostRepository:\n"
            '    """Post data access layer."""\n\n'
            "    def __init__(self, settings: DatabaseSettings):\n"
            "        self.db = WPostgreSQL(\n"
            "            Post,\n"
            "            settings.to_dict(),\n"
            "            pool_config={\n"
            '                "min_size": settings.pool_min_size,\n'
            '                "max_size": settings.pool_max_size,\n'
            "            },\n"
            "        )\n\n"
            "    def create(self, post: Post) -> None:\n"
            '        """Insert a new post."""\n'
            "        self.db.insert(post)\n\n"
            "    def get_by_user(self, user_id: int) -> list[Post]:\n"
            "        return self.db.get_by_field(user_id=user_id)\n\n"
            "    def get_all(self) -> list[Post]:\n"
            "        return self.db.get_all()\n\n"
            "    def update(self, post_id: int, post: Post) -> None:\n"
            "        self.db.update(post_id, post)\n\n"
            "    def delete(self, post_id: int) -> None:\n"
            "        self.db.delete(post_id)\n\n"
            "    # Async\n"
            "    async def create_async(self, post: Post) -> None:\n"
            "        self.db.insert(post)\n\n"
            "    async def get_by_user_async(self, user_id: int) -> list[Post]:\n"
            "        return await self.db.get_by_field_async(user_id=user_id)\n"
        )

        migrations_template = (
            "from wpostgresql import TableSync, AsyncTableSync\n"
            "from models.user import User\n"
            "from models.post import Post\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "def run_migrations(settings: DatabaseSettings) -> None:\n"
            '    """Run schema synchronization for all models."""\n'
            "    db_config = settings.to_dict()\n\n"
            "    # TableSync auto-creates tables and adds missing columns\n"
            "    TableSync(User, db_config).create_if_not_exists()\n"
            "    TableSync(User, db_config).sync_with_model()\n\n"
            "    TableSync(Post, db_config).create_if_not_exists()\n"
            "    TableSync(Post, db_config).sync_with_model()\n\n"
            "    # Create indexes\n"
            "    TableSync(User, db_config).create_index(['email'], 'idx_users_email', unique=True)\n"
            "    TableSync(Post, db_config).create_index(['user_id'], 'idx_posts_user_id')\n\n\n"
            "async def run_migrations_async(settings: DatabaseSettings) -> None:\n"
            '    """Async schema synchronization."""\n'
            "    db_config = settings.to_dict()\n\n"
            "    await AsyncTableSync(User, db_config).create_if_not_exists_async()\n"
            "    await AsyncTableSync(User, db_config).sync_with_model_async()\n\n"
            "    await AsyncTableSync(Post, db_config).create_if_not_exists_async()\n"
            "    await AsyncTableSync(Post, db_config).sync_with_model_async()\n"
        )

        main_template = (
            "from config.settings import DatabaseSettings\n"
            "from repositories.user_repo import UserRepository\n"
            "from repositories.post_repo import PostRepository\n"
            "from models.user import User\n"
            "from models.post import Post\n"
            "from migrations.manager import run_migrations\n\n\n"
            "def run_service() -> None:\n"
            '    """Orchestrator: wires every WPostgreSQL repository together."""\n'
            "    settings = DatabaseSettings.from_env()\n\n"
            "    # Run schema sync\n"
            "    run_migrations(settings)\n\n"
            "    users = UserRepository(settings)\n"
            "    posts = PostRepository(settings)\n\n"
            "    # Example usage\n"
            '    alice = User(id=1, name="Alice", email="alice@example.com", age=30)\n'
            "    users.create(alice)\n"
            '    print(f"Created user: {alice.id}")\n\n'
            '    post = Post(id=1, user_id=1, title="Hello WPostgreSQL", content="First post!")\n'
            "    posts.create(post)\n"
            '    print(f"Created post: {post.id}")\n\n'
            "    # List users with pagination\n"
            "    page = users.get_paginated(page=1, per_page=10)\n"
            "    for u in page:\n"
            '        print(f"User: {u.name} ({u.email})")\n\n'
            '    print(f"Total users: {users.count()}")\n\n\n'
            "async def run_service_async() -> None:\n"
            '    """Async orchestrator for FastAPI/Starlette."""\n'
            "    settings = DatabaseSettings.from_env()\n"
            "    from migrations.manager import run_migrations_async\n"
            "    await run_migrations_async(settings)\n\n"
            "    users = UserRepository(settings)\n"
            "    posts = PostRepository(settings)\n\n"
            '    bob = User(id=2, name="Bob", email="bob@example.com", age=25)\n'
            "    await users.create_async(bob)\n"
            '    print(f"Created user: {bob.id}")\n\n'
            "    all_users = await users.get_all_async()\n"
            "    for u in all_users:\n"
            '        print(f"User: {u.name}")\n\n\n'
            'if __name__ == "__main__":\n'
            "    import asyncio\n"
            "    run_service()\n"
            "    asyncio.run(run_service_async())\n"
        )

        test_repo_template = (
            '"""Tests for UserRepository."""\n\n'
            "from unittest import mock\n"
            "import pytest\n"
            "from models.user import User\n"
            "from repositories.user_repo import UserRepository\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "@pytest.fixture\n"
            "def settings():\n"
            '    return DatabaseSettings(dbname="testdb", user="test", password="test", host="localhost")\n\n\n'
            "@pytest.fixture\n"
            "def repo(settings):\n"
            "    with mock.patch('repositories.user_repo.WPostgreSQL') as MockDB:\n"
            "        instance = MockDB.return_value\n"
            "        yield UserRepository(settings), instance\n\n\n"
            "def test_create_calls_insert(repo):\n"
            "    r, db = repo\n"
            '    user = User(id=1, name="Alice", email="a@b.com", age=30)\n'
            "    r.create(user)\n"
            "    db.insert.assert_called_once_with(user)\n\n\n"
            "def test_get_all(repo):\n"
            "    r, db = repo\n"
            '    db.get_all.return_value = [User(id=1, name="Alice", email="a@b.com", age=30)]\n'
            "    result = r.get_all()\n"
            "    assert len(result) == 1\n"
            "    assert result[0].name == 'Alice'\n\n\n"
            "def test_get_by_id(repo):\n"
            "    r, db = repo\n"
            '    db.get_by_field.return_value = [User(id=1, name="Alice", email="a@b.com", age=30)]\n'
            "    result = r.get_by_id(1)\n"
            "    db.get_by_field.assert_called_with(id=1)\n"
            "    assert len(result) == 1\n\n\n"
            "def test_update_calls_update_with_model(repo):\n"
            "    r, db = repo\n"
            '    user = User(id=1, name="Alice Updated", email="a@b.com", age=31)\n'
            "    r.update(1, user)\n"
            "    db.update.assert_called_once_with(1, user)\n\n\n"
            "def test_delete(repo):\n"
            "    r, db = repo\n"
            "    r.delete(1)\n"
            "    db.delete.assert_called_once_with(1)\n\n\n"
            "def test_count(repo):\n"
            "    r, db = repo\n"
            "    db.count.return_value = 42\n"
            "    assert r.count() == 42\n"
        )

        test_post_repo_template = (
            '"""Tests for PostRepository."""\n\n'
            "from unittest import mock\n"
            "import pytest\n"
            "from models.post import Post\n"
            "from repositories.post_repo import PostRepository\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "@pytest.fixture\n"
            "def settings():\n"
            '    return DatabaseSettings(dbname="testdb", user="test", password="test", host="localhost")\n\n\n'
            "@pytest.fixture\n"
            "def repo(settings):\n"
            "    with mock.patch('repositories.post_repo.WPostgreSQL') as MockDB:\n"
            "        instance = MockDB.return_value\n"
            "        yield PostRepository(settings), instance\n\n\n"
            "def test_create_calls_insert(repo):\n"
            "    r, db = repo\n"
            '    post = Post(id=1, user_id=1, title="Hello", content="World")\n'
            "    r.create(post)\n"
            "    db.insert.assert_called_once_with(post)\n\n\n"
            "def test_get_by_user(repo):\n"
            "    r, db = repo\n"
            '    db.get_by_field.return_value = [Post(id=1, user_id=1, title="Hello", content="World")]\n'
            "    result = r.get_by_user(1)\n"
            "    db.get_by_field.assert_called_with(user_id=1)\n"
            "    assert len(result) == 1\n\n\n"
            "def test_update(repo):\n"
            "    r, db = repo\n"
            '    post = Post(id=1, user_id=1, title="Updated", content="New")\n'
            "    r.update(1, post)\n"
            "    db.update.assert_called_once_with(1, post)\n\n\n"
            "def test_delete(repo):\n"
            "    r, db = repo\n"
            "    r.delete(1)\n"
            "    db.delete.assert_called_once_with(1)\n"
        )

        # --- api_service routes ---
        users_route_template = (
            '"""User API routes."""\n\n'
            "from fastapi import APIRouter, HTTPException\n"
            "from pydantic import BaseModel as PydanticBaseModel\n"
            "from typing import Optional\n"
            "from models.user import User\n"
            "from repositories.user_repo import UserRepository\n"
            "from config.settings import DatabaseSettings\n\n\n"
            "router = APIRouter(prefix=\"/users\", tags=[\"users\"])\n"
            "_settings = DatabaseSettings.from_env()\n"
            "_repo = UserRepository(_settings)\n\n\n"
            "class UserCreate(PydanticBaseModel):\n"
            '    name: str\n'
            '    email: str = ""\n'
            "    age: int = 0\n"
            "    is_active: bool = True\n\n\n"
            "@router.get('/')\n"
            "async def list_users():\n"
            '    """List all users."""\n'
            "    return _repo.get_all()\n\n\n"
            "@router.get('/{user_id}')\n"
            "async def get_user(user_id: int):\n"
            '    """Get user by ID."""\n'
            "    results = _repo.get_by_id(user_id)\n"
            "    if not results:\n"
            "        raise HTTPException(status_code=404, detail='User not found')\n"
            "    return results[0]\n\n\n"
            "@router.post('/')\n"
            "async def create_user(data: UserCreate):\n"
            '    """Create a new user."""\n'
            "    user = User(id=0, name=data.name, email=data.email, age=data.age, is_active=data.is_active)\n"
            "    _repo.create(user)\n"
            "    return {'status': 'created', 'name': data.name}\n\n\n"
            "@router.put('/{user_id}')\n"
            "async def update_user(user_id: int, data: UserCreate):\n"
            '    """Update a user by ID."""\n'
            "    user = User(id=user_id, name=data.name, email=data.email, age=data.age, is_active=data.is_active)\n"
            "    _repo.update(user_id, user)\n"
            "    return {'status': 'updated'}\n\n\n"
            "@router.delete('/{user_id}')\n"
            "async def delete_user(user_id: int):\n"
            '    """Delete a user by ID."""\n'
            "    _repo.delete(user_id)\n"
            "    return {'status': 'deleted'}\n"
        )

        app_template = (
            '"""FastAPI application entrypoint."""\n\n'
            "from fastapi import FastAPI\n"
            "from config.settings import DatabaseSettings\n"
            "from migrations.manager import run_migrations\n"
            "from routes.users import router as users_router\n\n\n"
            "app = FastAPI(title='{project_name}', version='0.1.0')\n\n"
            "app.include_router(users_router)\n\n\n"
            "@app.on_event('startup')\n"
            "async def startup():\n"
            '    settings = DatabaseSettings.from_env()\n'
            "    run_migrations(settings)\n\n\n"
            "@app.get('/health')\n"
            "async def health():\n"
            '    return {{\'status\': \'ok\'}}\n'
        ).format(project_name=project_name)

        routes_init_template = "from .users import router\n"

        blueprints: dict[str, str] = {
            "requirements.txt": "wpostgresql>=1.0.0\npydantic>=2.0.0\nclick>=8.0.0\n",
            "README.md": (
                f"# {project_name.upper()}\n\n"
                "Professional PostgreSQL-backed architecture built with **wpostgresql**.\n\n"
                "## Architecture\n\n"
                "```\n"
                f"{project_name}/\n"
                "├── config/settings.py      # DatabaseSettings (from_env, to_dict)\n"
                "├── models/                 # Pydantic models (User, Post)\n"
                "├── repositories/           # Data access layer (WPostgreSQL wrappers)\n"
                "├── migrations/manager.py   # TableSync schema synchronization\n"
                "├── main.py                 # Orchestrator entrypoint\n"
                "└── tests/                  # pytest unit tests\n"
                "```\n\n"
                "## Quick Start\n\n"
                "```bash\n"
                "pip install wpostgresql\n"
                "python main.py\n"
                "```\n\n"
                "---\n*Generated by WPostgreSQL MCP by **wisrovi***\n"
            ),
            "config/__init__.py": "from .settings import DatabaseSettings\n",
            "config/settings.py": settings_template,
            "models/__init__.py": "from .user import User\nfrom .post import Post\n",
            "models/user.py": user_model_template,
            "models/post.py": post_model_template,
            "repositories/__init__.py": "from .user_repo import UserRepository\nfrom .post_repo import PostRepository\n",
            "repositories/user_repo.py": user_repo_template,
            "repositories/post_repo.py": post_repo_template,
            "migrations/__init__.py": "from .manager import run_migrations\n",
            "migrations/manager.py": migrations_template,
            "main.py": main_template,
            "tests/__init__.py": "",
            "tests/test_user_repo.py": test_repo_template,
            "tests/test_post_repo.py": test_post_repo_template,
        }

        if scaffold_type == "api_service":
            blueprints["requirements.txt"] += "fastapi>=0.100.0\nuvicorn>=0.23.0\npsycopg[binary]>=3.1.0\n"
            blueprints["routes/__init__.py"] = routes_init_template
            blueprints["routes/users.py"] = users_route_template
            blueprints["app.py"] = app_template

        return blueprints
