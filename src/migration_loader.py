
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

MIGRATIONS_DIR = Path("migrations")
MIGRATION_FILE_PATTERN = re.compile(r'^(\d{14})_(.+)\.(sql|py)$')


@dataclass
class MigrationFile:
    """Represents a migration file with its metadata."""
    version: str
    description: str
    file_path: Path
    file_type: str  # 'sql' or 'py'
    checksum: str
    content: str

    @property
    def timestamp(self) -> datetime:
        """Parse version as datetime."""
        return datetime.strptime(self.version, '%Y%m%d%H%M%S')

    def __lt__(self, other):
        """Enable sorting by version."""
        return self.version < other.version


def calculate_checksum(content: str) -> str:
    """Calculate SHA-256 checksum of migration content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def validate_migration_filename(filename: str) -> Optional[tuple]:
    """
    Validate migration file naming convention: YYYYMMDDHHMMSS_description.(sql|py)

    Returns:
        Tuple of (version, description, file_type) if valid, None otherwise.
    """
    match = MIGRATION_FILE_PATTERN.match(filename)
    if not match:
        return None

    version, description, file_type = match.groups()

    # Validate the timestamp is a valid date
    try:
        datetime.strptime(version, '%Y%m%d%H%M%S')
    except ValueError:
        return None

    return version, description, file_type


def load_migration_file(file_path: Path) -> Optional[MigrationFile]:
    """
    Load and parse a single migration file.

    Args:
        file_path: Path to the migration file

    Returns:
        MigrationFile object if valid, None if invalid
    """
    filename = file_path.name

    # Validate filename format
    parsed = validate_migration_filename(filename)
    if not parsed:
        print(f"Warning: Skipping invalid migration filename: {filename}")
        return None

    version, description, file_type = parsed

    # Read file content
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading migration file {filename}: {e}")
        return None

    # Calculate checksum
    checksum = calculate_checksum(content)

    return MigrationFile(
        version=version,
        description=description,
        file_path=file_path,
        file_type=file_type,
        checksum=checksum,
        content=content
    )


def scan_migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> List[MigrationFile]:
    """
    Scan the migrations directory and load all valid migration files.

    Args:
        migrations_dir: Path to migrations directory

    Returns:
        List of MigrationFile objects sorted by version (chronologically)
    """
    if not migrations_dir.exists():
        print(f"Warning: Migrations directory not found: {migrations_dir}")
        return []

    migration_files = []

    # Scan for .sql and .py files
    for file_path in migrations_dir.glob('*'):
        if file_path.is_file() and file_path.suffix in ['.sql', '.py']:
            migration_file = load_migration_file(file_path)
            if migration_file:
                migration_files.append(migration_file)

    # Sort by version (chronologically)
    migration_files.sort()

    return migration_files


def get_migration_by_version(version: str, migrations_dir: Path = MIGRATIONS_DIR) -> Optional[MigrationFile]:
    """
    Get a specific migration file by version.

    Args:
        version: Migration version (timestamp)
        migrations_dir: Path to migrations directory

    Returns:
        MigrationFile if found, None otherwise
    """
    all_migrations = scan_migration_files(migrations_dir)
    for migration in all_migrations:
        if migration.version == version:
            return migration
    return None


def generate_migration_filename(description: str, file_type: str = 'sql') -> str:
    """
    Generate a migration filename with current timestamp.

    Args:
        description: Migration description (will be sanitized)
        file_type: 'sql' or 'py'

    Returns:
        Generated filename following the convention
    """
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    # Sanitize description (replace spaces and special chars with underscores)
    sanitized_desc = re.sub(r'[^a-zA-Z0-9_]', '_', description.lower())
    sanitized_desc = re.sub(r'_+', '_', sanitized_desc).strip('_')

    return f"{timestamp}_{sanitized_desc}.{file_type}"


def create_migration_file(description: str, content: str = "", file_type: str = 'sql',
                          migrations_dir: Path = MIGRATIONS_DIR) -> Path:
    """
    Create a new migration file with the proper naming convention.

    Args:
        description: Migration description
        content: Initial content for the migration
        file_type: 'sql' or 'py'
        migrations_dir: Path to migrations directory

    Returns:
        Path to the created migration file
    """
    # Ensure migrations directory exists
    migrations_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = generate_migration_filename(description, file_type)
    file_path = migrations_dir / filename

    # Default content templates
    if not content:
        if file_type == 'sql':
            content = f"""-- Migration: {description}
-- Created: {datetime.now().isoformat()}

-- Add your migration SQL here
-- Example:
-- CREATE TABLE IF NOT EXISTS example_table (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL
-- );
"""
        else:  # Python migration
            content = f'''"""
Migration: {description}
Created: {datetime.now().isoformat()}
"""

def up(connection):
    """Apply the migration."""
    # Add your migration logic here
    pass


def down(connection):
    """Rollback the migration."""
    # Add your rollback logic here
    pass
'''

    # Write the file
    file_path.write_text(content, encoding='utf-8')
    print(f"Created migration: {filename}")

    return file_path
