import time
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import get_engine
from .migration_loader import MigrationFile, get_migration_by_version, scan_migration_files
from .migration_state import (
    PendingMigration,
    delete_migration_record,
    get_pending_migrations,
    record_migration_failure,
    record_migration_success,
)


class MigrationExecutionError(Exception):
    """Custom exception for migration execution errors."""

    pass


class MigrationExecutor:
    """Handles the execution of database migrations."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """
        Initialize the migration executor.

        Args:
            dry_run: If True, don't actually execute migrations, just validate
            verbose: If True, print detailed execution information
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.engine = get_engine()

    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[EXECUTOR] {message}")

    def _execute_sql_migration(self, migration: MigrationFile, connection) -> Optional[str]:
        """
        Execute a SQL migration file.

        Args:
            migration: MigrationFile object
            connection: Database connection

        Returns:
            Rollback SQL if extractable, None otherwise
        """
        self._log(f"Executing SQL migration: {migration.file_path.name}")

        # Split the SQL into individual statements
        statements = self._split_sql_statements(migration.content)

        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement or statement.startswith("--"):
                continue

            self._log(f"  Statement {i + 1}/{len(statements)}: {statement[:100]}...")

            if not self.dry_run:
                connection.execute(text(statement))

        # Try to generate rollback SQL (basic implementation)
        rollback_sql = self._generate_rollback_sql(migration.content)

        return rollback_sql

    def _execute_python_migration(self, migration: MigrationFile, connection) -> Optional[str]:
        """
        Execute a Python migration file.

        Args:
            migration: MigrationFile object
            connection: Database connection

        Returns:
            None (Python migrations should define their own rollback logic)
        """
        self._log(f"Executing Python migration: {migration.file_path.name}")

        # Import and execute the Python migration
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"migration_{migration.version}", migration.file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Call the up() function if it exists
        if hasattr(module, "up"):
            if not self.dry_run:
                module.up(connection)
            self._log("  Executed up() function")
        else:
            raise MigrationExecutionError(f"Python migration {migration.file_path.name} missing 'up()' function")

        return None  # Python migrations manage their own rollback

    def _split_sql_statements(self, sql: str) -> List[str]:
        """
        Split SQL content into individual statements.

        Args:
            sql: SQL content

        Returns:
            List of SQL statements
        """
        # Simple split by semicolon (doesn't handle complex cases like functions)
        statements = []
        current_statement = []

        for line in sql.split("\n"):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("--"):
                continue

            current_statement.append(line)

            # Check if statement ends with semicolon
            if stripped.endswith(";"):
                statements.append("\n".join(current_statement))
                current_statement = []

        # Add remaining statement if any
        if current_statement:
            statements.append("\n".join(current_statement))

        return statements

    def _generate_rollback_sql(self, sql: str) -> Optional[str]:
        """
        Attempt to generate rollback SQL for a migration.
        This is a basic implementation and may not work for all cases.

        Args:
            sql: Original migration SQL

        Returns:
            Rollback SQL if possible, None otherwise
        """
        sql_upper = sql.upper()

        # Extract table names from CREATE TABLE statements
        if "CREATE TABLE" in sql_upper:
            # Simple regex to find table names (not production-ready)
            import re

            matches = re.findall(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+)", sql, re.IGNORECASE)
            if matches:
                rollback_statements = [f"DROP TABLE IF EXISTS {table};" for table in matches]
                return "\n".join(rollback_statements)

        return None

    def execute_migration(self, migration: MigrationFile) -> Tuple[bool, float, Optional[str]]:
        """
        Execute a single migration within a transaction.

        Args:
            migration: MigrationFile to execute

        Returns:
            Tuple of (success: bool, execution_time: float, error_message: Optional[str])
        """
        start_time = time.time()
        error_message = None

        try:
            # Import here to avoid circular dependency
            from .schema_interceptor import migration_execution_context

            # Execute within migration context to bypass interceptor
            with migration_execution_context(migration.version):
                with self.engine.begin() as connection:
                    self._log(f"Starting migration: {migration.version} - {migration.description}")

                    # Execute based on file type
                    if migration.file_type == "sql":
                        rollback_sql = self._execute_sql_migration(migration, connection)
                    elif migration.file_type == "py":
                        rollback_sql = self._execute_python_migration(migration, connection)
                    else:
                        raise MigrationExecutionError(f"Unknown migration type: {migration.file_type}")

                    execution_time = time.time() - start_time

                    # Record success
                    if not self.dry_run:
                        record_migration_success(
                            version=migration.version,
                            description=migration.description,
                            checksum=migration.checksum,
                            execution_time=execution_time,
                            rollback_sql=rollback_sql,
                        )

                    self._log(f"Migration completed in {execution_time:.2f}s")
                    return True, execution_time, None

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

            self._log(f"Migration failed: {error_message}")

            # Record failure
            if not self.dry_run:
                try:
                    record_migration_failure(
                        version=migration.version,
                        description=migration.description,
                        checksum=migration.checksum,
                        execution_time=execution_time,
                        error_message=error_message,
                    )
                except Exception as record_error:
                    self._log(f"Failed to record migration failure: {record_error}")

            return False, execution_time, error_message

    def execute_pending_migrations(self) -> Tuple[int, int, List[str]]:
        """
        Execute all pending migrations in order.

        Returns:
            Tuple of (successful_count, failed_count, error_messages)
        """
        pending = get_pending_migrations()

        if not pending:
            self._log("No pending migrations to apply")
            return 0, 0, []

        self._log(f"Found {len(pending)} pending migrations")

        successful = 0
        failed = 0
        errors = []

        # Load migration files
        all_files = {f.version: f for f in scan_migration_files()}

        for pending_migration in pending:
            if pending_migration.version not in all_files:
                error_msg = f"Migration file not found: {pending_migration.version}"
                self._log(error_msg)
                errors.append(error_msg)
                failed += 1
                continue

            migration_file = all_files[pending_migration.version]

            # Execute the migration
            success, exec_time, error = self.execute_migration(migration_file)

            if success:
                successful += 1
                print(f"✓ Applied: {migration_file.version} - {migration_file.description} ({exec_time:.2f}s)")
            else:
                failed += 1
                print(f"✗ Failed: {migration_file.version} - {migration_file.description}")
                errors.append(f"Migration {migration_file.version} failed: {error}")

                # Stop on first failure
                self._log("Stopping migration execution due to failure")
                break

        return successful, failed, errors

    def rollback_migration(self, version: str) -> Tuple[bool, Optional[str]]:
        """
        Rollback a specific migration.

        Args:
            version: Migration version to rollback

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        from .migration_state import get_migration_by_version as get_applied_migration

        # Get the applied migration
        applied_migration = get_applied_migration(version)

        if not applied_migration:
            return False, f"Migration {version} is not applied"

        if not applied_migration.is_successful:
            return False, f"Migration {version} was not successful, cannot rollback"

        self._log(f"Rolling back migration: {version}")

        try:
            with self.engine.begin() as connection:
                # Execute rollback SQL if available
                if applied_migration.rollback_sql:
                    self._log("Executing rollback SQL")
                    statements = self._split_sql_statements(applied_migration.rollback_sql)

                    for statement in statements:
                        statement = statement.strip()
                        if statement:
                            connection.execute(text(statement))

                    self._log("Rollback SQL executed successfully")
                else:
                    self._log("No rollback SQL available")

                # Remove the migration record
                if not self.dry_run:
                    delete_migration_record(version)

            print(f"✓ Rolled back: {version}")
            return True, None

        except Exception as e:
            error_message = f"Rollback failed: {type(e).__name__}: {str(e)}"
            self._log(error_message)
            return False, error_message

    def rollback_last_n_migrations(self, n: int = 1) -> Tuple[int, int, List[str]]:
        """
        Rollback the last N successfully applied migrations.

        Args:
            n: Number of migrations to rollback

        Returns:
            Tuple of (successful_count, failed_count, error_messages)
        """
        from .migration_state import get_applied_migrations

        applied = get_applied_migrations()
        successful_applied = [m for m in applied if m.is_successful]

        if not successful_applied:
            self._log("No migrations to rollback")
            return 0, 0, []

        # Get the last N migrations
        to_rollback = successful_applied[:n]

        self._log(f"Rolling back {len(to_rollback)} migrations")

        successful = 0
        failed = 0
        errors = []

        for migration in to_rollback:
            success, error = self.rollback_migration(migration.version)

            if success:
                successful += 1
            else:
                failed += 1
                errors.append(error)

                # Stop on first failure
                self._log("Stopping rollback due to failure")
                break

        return successful, failed, errors


def apply_pending_migrations(dry_run: bool = False, verbose: bool = False) -> Tuple[int, int, List[str]]:
    """
    Convenience function to apply all pending migrations.

    Args:
        dry_run: If True, validate without executing
        verbose: If True, print detailed information

    Returns:
        Tuple of (successful_count, failed_count, error_messages)
    """
    executor = MigrationExecutor(dry_run=dry_run, verbose=verbose)
    return executor.execute_pending_migrations()


def rollback_migrations(count: int = 1, dry_run: bool = False, verbose: bool = False) -> Tuple[int, int, List[str]]:
    """
    Convenience function to rollback migrations.

    Args:
        count: Number of migrations to rollback
        dry_run: If True, validate without executing
        verbose: If True, print detailed information

    Returns:
        Tuple of (successful_count, failed_count, error_messages)
    """
    executor = MigrationExecutor(dry_run=dry_run, verbose=verbose)
    return executor.rollback_last_n_migrations(count)
