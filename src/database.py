from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .config import get_database_uri

_engine = None


def get_engine() -> Engine:
    """Returns a SQLAlchemy engine instance."""
    global _engine
    if _engine is None:
        db_uri = get_database_uri()
        try:
            _engine = create_engine(db_uri)
        except Exception as e:
            print(f"Error creating database engine: {e}")
            raise
    return _engine


def check_connection():
    """Checks if a connection to the database can be established."""
    try:
        engine = get_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connection successful.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
