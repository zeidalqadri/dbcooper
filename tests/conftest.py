"""
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Environment Setup
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["TESTING"] = "true"
    os.environ["ENFORCE_COMPLIANCE"] = "false"
    os.environ["ENABLE_AI_GENERATION"] = "false"
    yield
    # Cleanup
    os.environ.pop("TESTING", None)


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def test_db_engine() -> Generator[Engine, None, None]:
    """Create a test database engine with SQLite in-memory."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create schema_migrations table
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                description TEXT,
                checksum VARCHAR(64),
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time FLOAT,
                status VARCHAR(50) DEFAULT 'success',
                error_message TEXT
            )
        """
            )
        )
        conn.commit()

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine: Engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def mock_db_engine():
    """Mock database engine for unit tests that don't need real DB."""
    mock_engine = Mock(spec=Engine)
    mock_conn = Mock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    return mock_engine


# ============================================================================
# Migration Fixtures
# ============================================================================


@pytest.fixture
def sample_migration_sql() -> str:
    """Sample SQL migration content."""
    return """
-- Migration: Add users table
-- Description: Create users table with basic fields

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
"""


@pytest.fixture
def sample_migration_file(tmp_path: Path, sample_migration_sql: str) -> Path:
    """Create a sample migration file in a temporary directory."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    migration_file = migrations_dir / "20250101000000_add_users_table.sql"
    migration_file.write_text(sample_migration_sql)

    return migration_file


@pytest.fixture
def mock_migrations_dir(tmp_path: Path) -> Path:
    """Create a temporary migrations directory with sample migrations."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create multiple test migrations
    migrations = [
        ("20250101000000_initial_schema.sql", "CREATE TABLE test1 (id INT);"),
        ("20250101000001_add_users.sql", "CREATE TABLE users (id INT);"),
        ("20250101000002_add_posts.sql", "CREATE TABLE posts (id INT);"),
    ]

    for filename, content in migrations:
        (migrations_dir / filename).write_text(content)

    return migrations_dir


# ============================================================================
# AI Provider Fixtures
# ============================================================================


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("src.ai_providers.openai_provider.OpenAI") as mock:
        client = Mock()
        mock.return_value = client

        # Mock completion response
        client.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="CREATE TABLE test (id INT);"))],
            usage=Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )

        yield client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic Claude client."""
    with patch("src.ai_providers.claude_provider.Anthropic") as mock:
        client = Mock()
        mock.return_value = client

        # Mock message response
        client.messages.create.return_value = Mock(
            content=[Mock(text="CREATE TABLE test (id INT);")], usage=Mock(input_tokens=100, output_tokens=50)
        )

        yield client


# ============================================================================
# API Fixtures
# ============================================================================


@pytest.fixture
def mock_fastapi_app():
    """Mock FastAPI application for testing."""
    from fastapi import FastAPI

    app = FastAPI()
    return app


# ============================================================================
# Compliance Fixtures
# ============================================================================


@pytest.fixture
def sample_destructive_sql() -> str:
    """Sample SQL with destructive operations."""
    return """
DROP TABLE users;
TRUNCATE TABLE posts;
DELETE FROM comments WHERE id > 0;
"""


@pytest.fixture
def sample_safe_sql() -> str:
    """Sample safe SQL without destructive operations."""
    return """
CREATE TABLE new_users (
    id INT PRIMARY KEY,
    name VARCHAR(255)
);
ALTER TABLE users ADD COLUMN age INT;
CREATE INDEX idx_users_age ON users(age);
"""


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration values."""
    config = {
        "DATABASE_URL": "sqlite:///:memory:",
        "MIGRATIONS_DIR": "migrations",
        "ENFORCE_COMPLIANCE": True,
        "ALLOW_DESTRUCTIVE_MIGRATIONS": False,
        "ENABLE_AI_GENERATION": False,
    }

    with patch.dict(os.environ, config):
        yield config


@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture log messages."""
    import logging

    caplog.set_level(logging.INFO)
    return caplog
