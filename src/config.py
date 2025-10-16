
import os
from pathlib import Path

DB_URI_FILE = Path(".db_uri")

def get_database_uri() -> str:
    """
    Retrieves the database connection URI.

    The URI is retrieved from the following sources in order:
    1. Environment variable `DATABASE_URL`.
    2. A file named `.db_uri` in the project root.

    If neither is found, it prompts the user to enter one.
    """
    db_uri = os.environ.get("DATABASE_URL")
    if db_uri:
        return db_uri

    if DB_URI_FILE.exists():
        db_uri = DB_URI_FILE.read_text().strip()
        if db_uri:
            return db_uri

    db_uri = input("Please enter the database connection URI: ").strip()
    if not db_uri:
        raise ValueError("Database URI cannot be empty.")

    # Save the URI for future use
    save_uri = input("Do you want to save this URI in .db_uri for future use? (y/n): ").lower()
    if save_uri == 'y':
        DB_URI_FILE.write_text(db_uri)
        print(f"URI saved to {DB_URI_FILE.resolve()}")

    return db_uri
