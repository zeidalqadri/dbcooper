import hashlib
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import DDL, Column, DateTime, Float, MetaData, String, Table, Text, create_engine, event

from .database import get_engine

MIGRATIONS_DIR = Path("migrations")
SCHEMA_TABLE_NAME = "schema_migrations"

metadata = MetaData()

schema_migrations_table = Table(
    SCHEMA_TABLE_NAME,
    metadata,
    Column("version", String, primary_key=True),
    Column("description", String, nullable=False),
    Column("applied_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("checksum", String, nullable=False),
    Column("status", String, nullable=False, default="success"),  # success, failed, pending
    Column("execution_time", Float, nullable=True),  # Time in seconds
    Column("error_message", Text, nullable=True),  # Error details if failed
    Column("rollback_sql", Text, nullable=True),  # SQL to rollback this migration
)


def initialize_db():
    """
    Initializes the database by creating the schema_migrations table if it doesn't exist.
    """
    engine = get_engine()
    if not engine.dialect.has_table(engine.connect(), SCHEMA_TABLE_NAME):
        print(f"Creating schema migrations table: {SCHEMA_TABLE_NAME}")
        try:
            metadata.create_all(engine)
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    else:
        print("Database is already initialized.")
