from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from .database import get_engine
from .migration_loader import MigrationFile, scan_migration_files
from .migration_manager import SCHEMA_TABLE_NAME, schema_migrations_table


@dataclass
class AppliedMigration:
    """Represents a migration that has been applied to the database."""

    version: str
    description: str
    applied_at: datetime
    checksum: str
    status: str  # success, failed, pending
    execution_time: Optional[float]
    error_message: Optional[str]
    rollback_sql: Optional[str]

    @property
    def is_successful(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    def __lt__(self, other):
        """Enable sorting by version."""
        return self.version < other.version


@dataclass
class PendingMigration:
    """Represents a migration file that hasn't been applied yet."""

    version: str
    description: str
    file_path: str
    checksum: str
    file_type: str

    def __lt__(self, other):
        """Enable sorting by version."""
        return self.version < other.version


@dataclass
class MigrationStateReport:
    """Comprehensive report of migration state."""

    applied_count: int
    pending_count: int
    failed_count: int
    last_applied_version: Optional[str]
    last_applied_timestamp: Optional[datetime]
    applied_migrations: List[AppliedMigration]
    pending_migrations: List[PendingMigration]
    checksum_mismatches: List[Dict[str, str]]
    orphaned_migrations: List[AppliedMigration]  # In DB but file not found

    @property
    def has_pending(self) -> bool:
        return self.pending_count > 0

    @property
    def has_failed(self) -> bool:
        return self.failed_count > 0

    @property
    def has_checksum_mismatches(self) -> bool:
        return len(self.checksum_mismatches) > 0

    @property
    def has_orphaned(self) -> bool:
        return len(self.orphaned_migrations) > 0

    @property
    def is_compliant(self) -> bool:
        """Check if system is in compliant state (no pending, failed, or mismatches)."""
        return not (self.has_pending or self.has_failed or self.has_checksum_mismatches)


def table_exists(engine) -> bool:
    """Check if schema_migrations table exists."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{SCHEMA_TABLE_NAME}')")
            )
            return result.scalar()
    except Exception:
        return False


def get_applied_migrations() -> List[AppliedMigration]:
    """
    Retrieve all applied migrations from the database, ordered by version DESC.

    Returns:
        List of AppliedMigration objects
    """
    engine = get_engine()

    # Check if table exists
    if not table_exists(engine):
        return []

    try:
        with engine.connect() as conn:
            stmt = select(schema_migrations_table).order_by(schema_migrations_table.c.version.desc())
            result = conn.execute(stmt)

            migrations = []
            for row in result:
                migrations.append(
                    AppliedMigration(
                        version=row.version,
                        description=row.description,
                        applied_at=row.applied_at,
                        checksum=row.checksum,
                        status=row.status,
                        execution_time=row.execution_time,
                        error_message=row.error_message,
                        rollback_sql=row.rollback_sql,
                    )
                )

            return migrations

    except SQLAlchemyError as e:
        print(f"Error retrieving applied migrations: {e}")
        raise


def get_pending_migrations() -> List[PendingMigration]:
    """
    Get all migrations that haven't been applied yet.

    Returns:
        List of PendingMigration objects sorted by version
    """
    # Get all migration files
    all_files = scan_migration_files()

    # Get applied migrations
    applied = get_applied_migrations()
    applied_versions = {m.version for m in applied}

    # Find pending migrations
    pending = []
    for file in all_files:
        if file.version not in applied_versions:
            pending.append(
                PendingMigration(
                    version=file.version,
                    description=file.description,
                    file_path=str(file.file_path),
                    checksum=file.checksum,
                    file_type=file.file_type,
                )
            )

    pending.sort()
    return pending


def get_failed_migrations() -> List[AppliedMigration]:
    """
    Get all migrations that failed during application.

    Returns:
        List of AppliedMigration objects with status='failed'
    """
    applied = get_applied_migrations()
    return [m for m in applied if m.is_failed]


def get_checksum_mismatches() -> List[Dict[str, str]]:
    """
    Detect migrations where the checksum in the database doesn't match the file.
    This indicates the migration file has been modified after being applied.

    Returns:
        List of dictionaries with mismatch details
    """
    all_files = scan_migration_files()
    applied = get_applied_migrations()

    # Create lookup for applied migrations
    applied_dict = {m.version: m for m in applied}

    mismatches = []
    for file in all_files:
        if file.version in applied_dict:
            applied_migration = applied_dict[file.version]
            if file.checksum != applied_migration.checksum:
                mismatches.append(
                    {
                        "version": file.version,
                        "description": file.description,
                        "file_checksum": file.checksum,
                        "db_checksum": applied_migration.checksum,
                        "file_path": str(file.file_path),
                    }
                )

    return mismatches


def get_orphaned_migrations() -> List[AppliedMigration]:
    """
    Find migrations that are in the database but their files no longer exist.

    Returns:
        List of AppliedMigration objects that are orphaned
    """
    all_files = scan_migration_files()
    applied = get_applied_migrations()

    # Create set of file versions
    file_versions = {f.version for f in all_files}

    # Find orphaned migrations
    orphaned = [m for m in applied if m.version not in file_versions]

    return orphaned


def get_migration_state_report() -> MigrationStateReport:
    """
    Generate a comprehensive migration state report.

    Returns:
        MigrationStateReport with all migration statistics and details
    """
    applied = get_applied_migrations()
    pending = get_pending_migrations()
    failed = get_failed_migrations()
    mismatches = get_checksum_mismatches()
    orphaned = get_orphaned_migrations()

    # Get last applied migration
    last_applied_version = None
    last_applied_timestamp = None
    if applied:
        # Applied migrations are already sorted DESC
        last_applied_version = applied[0].version
        last_applied_timestamp = applied[0].applied_at

    return MigrationStateReport(
        applied_count=len(applied),
        pending_count=len(pending),
        failed_count=len(failed),
        last_applied_version=last_applied_version,
        last_applied_timestamp=last_applied_timestamp,
        applied_migrations=applied,
        pending_migrations=pending,
        checksum_mismatches=mismatches,
        orphaned_migrations=orphaned,
    )


def get_migration_by_version(version: str) -> Optional[AppliedMigration]:
    """
    Get a specific applied migration by version.

    Args:
        version: Migration version to retrieve

    Returns:
        AppliedMigration if found, None otherwise
    """
    applied = get_applied_migrations()
    for migration in applied:
        if migration.version == version:
            return migration
    return None


def record_migration_success(
    version: str, description: str, checksum: str, execution_time: float, rollback_sql: Optional[str] = None
):
    """
    Record a successful migration application.

    Args:
        version: Migration version
        description: Migration description
        checksum: Migration file checksum
        execution_time: Time taken to execute in seconds
        rollback_sql: Optional SQL to rollback the migration
    """
    engine = get_engine()

    try:
        with engine.begin() as conn:
            stmt = schema_migrations_table.insert().values(
                version=version,
                description=description,
                applied_at=datetime.utcnow(),
                checksum=checksum,
                status="success",
                execution_time=execution_time,
                error_message=None,
                rollback_sql=rollback_sql,
            )
            conn.execute(stmt)

    except SQLAlchemyError as e:
        print(f"Error recording migration success: {e}")
        raise


def record_migration_failure(version: str, description: str, checksum: str, execution_time: float, error_message: str):
    """
    Record a failed migration attempt.

    Args:
        version: Migration version
        description: Migration description
        checksum: Migration file checksum
        execution_time: Time taken before failure in seconds
        error_message: Error details
    """
    engine = get_engine()

    try:
        with engine.begin() as conn:
            stmt = schema_migrations_table.insert().values(
                version=version,
                description=description,
                applied_at=datetime.utcnow(),
                checksum=checksum,
                status="failed",
                execution_time=execution_time,
                error_message=error_message,
                rollback_sql=None,
            )
            conn.execute(stmt)

    except SQLAlchemyError as e:
        print(f"Error recording migration failure: {e}")
        raise


def delete_migration_record(version: str):
    """
    Delete a migration record from the database.
    Used for rollback operations.

    Args:
        version: Migration version to delete
    """
    engine = get_engine()

    try:
        with engine.begin() as conn:
            stmt = schema_migrations_table.delete().where(schema_migrations_table.c.version == version)
            conn.execute(stmt)

    except SQLAlchemyError as e:
        print(f"Error deleting migration record: {e}")
        raise
