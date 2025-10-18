import os
from pathlib import Path
from typing import Optional

DB_URI_FILE = Path(".db_uri")


def get_database_uri() -> str:
    """
    Retrieves the database connection URI.

    The URI is retrieved from the following sources in order:
    1. Environment variable `DATABASE_URL`.
    2. A file named `.db_uri` in the project root (for local development only).

    Raises:
        ValueError: If DATABASE_URL is not set and .db_uri file doesn't exist.

    Security Note:
        - In production, always use DATABASE_URL environment variable
        - Never commit .db_uri file (it's in .gitignore)
        - Use proper secret management in production environments
    """
    # Priority 1: Environment variable (production standard)
    db_uri = os.environ.get("DATABASE_URL")
    if db_uri:
        return db_uri

    # Priority 2: Local development file (fallback only)
    if DB_URI_FILE.exists():
        db_uri = DB_URI_FILE.read_text().strip()
        if db_uri:
            return db_uri

    # Fail fast with clear instructions
    raise ValueError(
        "Database URI not configured. Set the DATABASE_URL environment variable.\n"
        "Example: export DATABASE_URL='postgresql://user:password@localhost:5432/dbname'\n"
        "For local development, you can also create a .db_uri file with the connection string."
    )


def get_config_value(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Get a configuration value from environment variables.

    Args:
        key: The environment variable name
        default: Default value if not found
        required: If True, raises ValueError when not found

    Returns:
        The configuration value or default

    Raises:
        ValueError: If required=True and value not found
    """
    value = os.environ.get(key, default)
    if required and value is None:
        raise ValueError(f"Required configuration '{key}' not set. Check .env.example for details.")
    return value


# API Configuration
API_HOST = get_config_value("API_HOST", "0.0.0.0")
API_PORT = int(get_config_value("API_PORT", "8000"))
API_RELOAD = get_config_value("API_RELOAD", "false").lower() == "true"

# CORS Configuration
CORS_ORIGINS = get_config_value("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# Logging Configuration
LOG_LEVEL = get_config_value("LOG_LEVEL", "INFO")
LOG_FORMAT = get_config_value("LOG_FORMAT", "json")

# Migration Configuration
MIGRATIONS_DIR = get_config_value("MIGRATIONS_DIR", "migrations")
MIGRATION_TABLE = get_config_value("MIGRATION_TABLE", "schema_migrations")

# Compliance Configuration
ENFORCE_COMPLIANCE = get_config_value("ENFORCE_COMPLIANCE", "true").lower() == "true"
ALLOW_DESTRUCTIVE_MIGRATIONS = get_config_value("ALLOW_DESTRUCTIVE_MIGRATIONS", "false").lower() == "true"

# Feature Flags
ENABLE_AI_GENERATION = get_config_value("ENABLE_AI_GENERATION", "true").lower() == "true"
ENABLE_SCHEMA_INTERCEPTION = get_config_value("ENABLE_SCHEMA_INTERCEPTION", "true").lower() == "true"
ENABLE_WEBSOCKET = get_config_value("ENABLE_WEBSOCKET", "true").lower() == "true"
