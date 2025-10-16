
import re
import threading
from contextlib import contextmanager
from typing import Optional, Set
from datetime import datetime

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from .compliance_checker import enforce_migration_compliance, ComplianceViolationError
from .database import get_engine


# Thread-local storage for migration context
_migration_context = threading.local()


class SchemaInterceptor:
    """
    Application-level middleware for intercepting and controlling schema modifications.
    Uses SQLAlchemy event listeners to intercept DDL statements before execution.
    """

    # DDL statement patterns to intercept
    DDL_PATTERNS = [
        r'^\s*CREATE\s+TABLE',
        r'^\s*ALTER\s+TABLE',
        r'^\s*DROP\s+TABLE',
        r'^\s*CREATE\s+INDEX',
        r'^\s*DROP\s+INDEX',
        r'^\s*CREATE\s+SCHEMA',
        r'^\s*DROP\s+SCHEMA',
        r'^\s*CREATE\s+SEQUENCE',
        r'^\s*DROP\s+SEQUENCE',
        r'^\s*CREATE\s+TYPE',
        r'^\s*DROP\s+TYPE',
        r'^\s*TRUNCATE\s+TABLE',
    ]

    # Statements that should NOT trigger compliance checks
    BYPASS_PATTERNS = [
        r'^\s*CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+schema_migrations',
        r'^\s*CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+ddl_audit_log',
        r'^\s*CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+migration_execution_context',
        r'^\s*SELECT',
        r'^\s*INSERT',
        r'^\s*UPDATE',
        r'^\s*DELETE',
        r'^\s*BEGIN',
        r'^\s*COMMIT',
        r'^\s*ROLLBACK',
    ]

    def __init__(self, engine: Optional[Engine] = None, strict_mode: bool = True):
        """
        Initialize the schema interceptor.

        Args:
            engine: SQLAlchemy engine to attach listeners to
            strict_mode: If True, enforce compliance checks on all DDL
        """
        self.engine = engine or get_engine()
        self.strict_mode = strict_mode
        self.enabled = False
        self._ddl_patterns_compiled = [re.compile(p, re.IGNORECASE) for p in self.DDL_PATTERNS]
        self._bypass_patterns_compiled = [re.compile(p, re.IGNORECASE) for p in self.BYPASS_PATTERNS]

    def _is_ddl_statement(self, statement: str) -> bool:
        """Check if a statement is a DDL operation."""
        for pattern in self._ddl_patterns_compiled:
            if pattern.match(statement):
                return True
        return False

    def _should_bypass(self, statement: str) -> bool:
        """Check if a statement should bypass compliance checks."""
        for pattern in self._bypass_patterns_compiled:
            if pattern.match(statement):
                return True
        return False

    def _is_in_migration_context(self) -> bool:
        """Check if we're currently executing within a migration context."""
        return getattr(_migration_context, 'active', False)

    def _get_migration_version(self) -> Optional[str]:
        """Get the current migration version if in migration context."""
        return getattr(_migration_context, 'version', None)

    def _before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        """
        Event listener called before SQL execution.
        Intercepts DDL statements and enforces compliance.
        """
        # Skip if interceptor is disabled
        if not self.enabled:
            return

        # Check if this is a DDL statement
        if not self._is_ddl_statement(statement):
            return

        # Check if we should bypass compliance check
        if self._should_bypass(statement):
            return

        # If we're in a migration context, allow the operation
        if self._is_in_migration_context():
            migration_version = self._get_migration_version()
            print(f"[INTERCEPTOR] Allowing DDL in migration context: {migration_version}")
            self._log_ddl_operation(statement, blocked=False, migration_version=migration_version)
            return

        # Not in migration context - enforce compliance
        if self.strict_mode:
            print(f"[INTERCEPTOR] Intercepted DDL statement: {statement[:100]}...")

            try:
                # This will raise ComplianceViolationError if violations exist
                enforce_migration_compliance(operation=f"DDL: {statement[:50]}...")
                print("[INTERCEPTOR] Compliance check passed - allowing DDL")
                self._log_ddl_operation(statement, blocked=False)

            except ComplianceViolationError as e:
                print(f"[INTERCEPTOR] BLOCKING DDL - Compliance violation: {str(e)[:200]}")
                self._log_ddl_operation(statement, blocked=True, block_reason=str(e))

                # Re-raise the exception to prevent execution
                raise

    def _log_ddl_operation(self, statement: str, blocked: bool,
                           migration_version: Optional[str] = None,
                           block_reason: Optional[str] = None):
        """
        Log DDL operation to the audit log.

        Args:
            statement: SQL statement
            blocked: Whether the operation was blocked
            migration_version: Migration version if in migration context
            block_reason: Reason for blocking if applicable
        """
        try:
            # Extract operation type
            match = re.match(r'^\s*(\w+)\s+(\w+)', statement, re.IGNORECASE)
            event_type = match.group(1).upper() if match else 'UNKNOWN'
            object_type = match.group(2).upper() if match and match.lastindex >= 2 else None

            # Log to ddl_audit_log table
            with self.engine.begin() as conn:
                # Check if table exists first
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ddl_audit_log')"
                ))
                if not result.scalar():
                    return  # Table doesn't exist yet, skip logging

                log_stmt = text("""
                    INSERT INTO ddl_audit_log (
                        event_type, object_type, sql_command, blocked,
                        block_reason, migration_context, user_name, application_name
                    ) VALUES (
                        :event_type, :object_type, :sql_command, :blocked,
                        :block_reason, :migration_context, current_user, current_setting('application_name', true)
                    )
                """)

                conn.execute(log_stmt, {
                    'event_type': event_type,
                    'object_type': object_type,
                    'sql_command': statement[:5000],  # Limit to 5000 chars
                    'blocked': blocked,
                    'block_reason': block_reason,
                    'migration_context': migration_version
                })

        except Exception as e:
            print(f"[INTERCEPTOR] Warning: Failed to log DDL operation: {e}")

    def enable(self):
        """Enable the schema interceptor."""
        if not self.enabled:
            event.listen(
                self.engine,
                'before_cursor_execute',
                self._before_cursor_execute,
                retval=False
            )
            self.enabled = True
            print("[INTERCEPTOR] Schema interceptor ENABLED")

    def disable(self):
        """Disable the schema interceptor."""
        if self.enabled:
            event.remove(
                self.engine,
                'before_cursor_execute',
                self._before_cursor_execute
            )
            self.enabled = False
            print("[INTERCEPTOR] Schema interceptor DISABLED")

    @contextmanager
    def migration_context(self, migration_version: str):
        """
        Context manager for executing migrations with bypass enabled.

        Args:
            migration_version: Version of the migration being executed

        Usage:
            with interceptor.migration_context('20240101120000'):
                # DDL operations allowed here
                execute_migration()
        """
        # Set migration context
        _migration_context.active = True
        _migration_context.version = migration_version

        # Mark migration start in database
        try:
            with self.engine.begin() as conn:
                # Check if function exists
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM pg_proc WHERE proname = 'migration_start')"
                ))
                if result.scalar():
                    conn.execute(text("SELECT migration_start(:version)"), {'version': migration_version})
        except Exception as e:
            print(f"[INTERCEPTOR] Warning: Could not mark migration start: {e}")

        try:
            print(f"[INTERCEPTOR] Entered migration context: {migration_version}")
            yield

        finally:
            # Mark migration end in database
            try:
                with self.engine.begin() as conn:
                    result = conn.execute(text(
                        "SELECT EXISTS (SELECT FROM pg_proc WHERE proname = 'migration_end')"
                    ))
                    if result.scalar():
                        conn.execute(text("SELECT migration_end(:version)"), {'version': migration_version})
            except Exception as e:
                print(f"[INTERCEPTOR] Warning: Could not mark migration end: {e}")

            # Clear migration context
            _migration_context.active = False
            _migration_context.version = None
            print(f"[INTERCEPTOR] Exited migration context: {migration_version}")


# Global interceptor instance
_global_interceptor: Optional[SchemaInterceptor] = None


def get_interceptor() -> SchemaInterceptor:
    """Get the global schema interceptor instance."""
    global _global_interceptor
    if _global_interceptor is None:
        _global_interceptor = SchemaInterceptor()
    return _global_interceptor


def enable_schema_interception(strict_mode: bool = True):
    """
    Enable global schema interception.

    Args:
        strict_mode: If True, enforce compliance checks on all DDL
    """
    interceptor = get_interceptor()
    interceptor.strict_mode = strict_mode
    interceptor.enable()


def disable_schema_interception():
    """Disable global schema interception."""
    interceptor = get_interceptor()
    interceptor.disable()


@contextmanager
def migration_execution_context(migration_version: str):
    """
    Context manager for migration execution with proper interception bypass.

    Args:
        migration_version: Version of the migration being executed

    Usage:
        with migration_execution_context('20240101120000'):
            execute_migration_sql()
    """
    interceptor = get_interceptor()
    with interceptor.migration_context(migration_version):
        yield
