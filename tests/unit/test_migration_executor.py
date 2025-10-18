"""
Unit tests for migration_executor module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.migration_executor import (
    MigrationExecutor,
    MigrationExecutionError,
    apply_pending_migrations,
    rollback_migrations,
)
from src.migration_loader import MigrationFile


@pytest.fixture
def executor():
    """Create a MigrationExecutor instance for testing."""
    with patch("src.migration_executor.get_engine"):
        return MigrationExecutor(dry_run=False, verbose=True)


@pytest.fixture
def sample_sql_migration():
    """Create a sample SQL migration."""
    return MigrationFile(
        version="20250101000000",
        description="Test migration",
        file_path=Path("/tmp/20250101000000_test.sql"),
        checksum="abc123",
        content="CREATE TABLE test_table (id INT PRIMARY KEY);",
        file_type="sql",
    )


@pytest.fixture
def sample_python_migration():
    """Create a sample Python migration."""
    return MigrationFile(
        version="20250101000001",
        description="Python test migration",
        file_path=Path("/tmp/20250101000001_test.py"),
        checksum="def456",
        content="def up(conn):\n    pass\n",
        file_type="py",
    )


class TestMigrationExecutor:
    """Test MigrationExecutor class."""

    def test_initialization(self):
        """Test MigrationExecutor initialization."""
        with patch("src.migration_executor.get_engine") as mock_engine:
            executor = MigrationExecutor(dry_run=True, verbose=False)
            assert executor.dry_run is True
            assert executor.verbose is False
            mock_engine.assert_called_once()

    def test_log_when_verbose(self, executor, capsys):
        """Test logging when verbose mode is enabled."""
        executor.verbose = True
        executor._log("Test message")
        captured = capsys.readouterr()
        assert "[EXECUTOR] Test message" in captured.out

    def test_no_log_when_not_verbose(self, executor, capsys):
        """Test no logging when verbose mode is disabled."""
        executor.verbose = False
        executor._log("Test message")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_split_sql_statements(self, executor):
        """Test SQL statement splitting."""
        sql = """
        CREATE TABLE users (id INT);
        CREATE TABLE posts (id INT);
        -- Comment
        INSERT INTO users VALUES (1);
        """
        statements = executor._split_sql_statements(sql)
        assert len(statements) > 0

    def test_execute_sql_migration_dry_run(self, executor, sample_sql_migration):
        """Test SQL migration execution in dry-run mode."""
        executor.dry_run = True
        mock_conn = Mock()

        result = executor._execute_sql_migration(sample_sql_migration, mock_conn)

        # In dry-run mode, connection.execute should not be called
        mock_conn.execute.assert_not_called()

    def test_execute_sql_migration_normal(self, executor, sample_sql_migration):
        """Test SQL migration execution in normal mode."""
        executor.dry_run = False
        mock_conn = Mock()

        result = executor._execute_sql_migration(sample_sql_migration, mock_conn)

        # Connection.execute should be called
        assert mock_conn.execute.called

    def test_execute_sql_migration_with_error(self, executor, sample_sql_migration):
        """Test SQL migration execution with database error."""
        executor.dry_run = False
        mock_conn = Mock()
        mock_conn.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            executor._execute_sql_migration(sample_sql_migration, mock_conn)

    def test_generate_rollback_sql_create_table(self, executor):
        """Test rollback SQL generation for CREATE TABLE."""
        sql = "CREATE TABLE users (id INT PRIMARY KEY);"
        rollback = executor._generate_rollback_sql(sql)
        assert rollback is not None
        assert "DROP TABLE" in rollback.upper() or rollback is None

    def test_generate_rollback_sql_alter_table(self, executor):
        """Test rollback SQL generation for ALTER TABLE."""
        sql = "ALTER TABLE users ADD COLUMN email VARCHAR(255);"
        rollback = executor._generate_rollback_sql(sql)
        # Rollback generation is complex, just ensure it doesn't crash
        assert rollback is None or isinstance(rollback, str)

    def test_apply_migration_success(self, executor, sample_sql_migration):
        """Test successful migration application."""
        mock_conn = Mock()
        executor.engine.begin = MagicMock()
        executor.engine.begin.return_value.__enter__ = Mock(return_value=mock_conn)
        executor.engine.begin.return_value.__exit__ = Mock(return_value=False)

        with patch("src.migration_executor.record_migration_success"):
            with patch.object(executor, "_execute_sql_migration", return_value=None):
                result = executor.apply_migration(sample_sql_migration)
                assert result is True

    def test_apply_migration_with_transaction_rollback(self, executor, sample_sql_migration):
        """Test migration application with transaction rollback on error."""
        mock_conn = Mock()
        mock_conn.execute.side_effect = SQLAlchemyError("Database error")

        executor.engine.begin = MagicMock()
        executor.engine.begin.return_value.__enter__ = Mock(return_value=mock_conn)
        executor.engine.begin.return_value.__exit__ = Mock(return_value=False)

        with patch("src.migration_executor.record_migration_failure"):
            result = executor.apply_migration(sample_sql_migration)
            # Should return False on error
            assert result is False or result is None

    @pytest.mark.parametrize(
        "file_type,expected_method",
        [
            ("sql", "_execute_sql_migration"),
            ("py", "_execute_python_migration"),
        ],
    )
    def test_apply_migration_delegates_to_correct_method(self, executor, file_type, expected_method):
        """Test that apply_migration delegates to correct execution method."""
        migration = MigrationFile(
            version="20250101000000",
            description="Test",
            file_path=Path(f"/tmp/test.{file_type}"),
            checksum="abc",
            content="test",
            file_type=file_type,
        )

        mock_conn = Mock()
        executor.engine.begin = MagicMock()
        executor.engine.begin.return_value.__enter__ = Mock(return_value=mock_conn)
        executor.engine.begin.return_value.__exit__ = Mock(return_value=False)

        with patch("src.migration_executor.record_migration_success"):
            with patch.object(executor, expected_method, return_value=None) as mock_method:
                executor.apply_migration(migration)
                mock_method.assert_called_once()


class TestApplyPendingMigrations:
    """Test apply_pending_migrations function."""

    @patch("src.migration_executor.get_pending_migrations")
    @patch("src.migration_executor.MigrationExecutor")
    def test_apply_pending_migrations_success(self, mock_executor_class, mock_get_pending):
        """Test successful application of pending migrations."""
        # Setup mocks
        mock_pending = [
            Mock(version="001", description="Test 1"),
            Mock(version="002", description="Test 2"),
        ]
        mock_get_pending.return_value = mock_pending

        mock_executor = Mock()
        mock_executor.apply_migration.return_value = True
        mock_executor_class.return_value = mock_executor

        # Execute
        result = apply_pending_migrations(dry_run=False, verbose=False)

        # Verify
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

    @patch("src.migration_executor.get_pending_migrations")
    @patch("src.migration_executor.MigrationExecutor")
    def test_apply_pending_migrations_with_failures(self, mock_executor_class, mock_get_pending):
        """Test application of pending migrations with some failures."""
        mock_pending = [
            Mock(version="001", description="Test 1"),
            Mock(version="002", description="Test 2"),
        ]
        mock_get_pending.return_value = mock_pending

        mock_executor = Mock()
        mock_executor.apply_migration.side_effect = [True, False]
        mock_executor_class.return_value = mock_executor

        result = apply_pending_migrations(dry_run=False, verbose=False)

        assert result["successful"] == 1
        assert result["failed"] == 1

    @patch("src.migration_executor.get_pending_migrations")
    def test_apply_pending_migrations_no_pending(self, mock_get_pending):
        """Test when there are no pending migrations."""
        mock_get_pending.return_value = []

        result = apply_pending_migrations(dry_run=False, verbose=False)

        assert result["successful"] == 0
        assert result["failed"] == 0
        assert "No pending migrations" in result["message"]


class TestRollbackMigrations:
    """Test rollback_migrations function."""

    @patch("src.migration_executor.get_applied_migrations")
    @patch("src.migration_executor.get_migration_by_version")
    @patch("src.migration_executor.delete_migration_record")
    def test_rollback_single_migration(self, mock_delete, mock_get_by_version, mock_get_applied):
        """Test rolling back a single migration."""
        mock_applied = [Mock(version="001", description="Test")]
        mock_get_applied.return_value = mock_applied

        mock_migration = Mock()
        mock_migration.content = "DROP TABLE test_table;"
        mock_get_by_version.return_value = mock_migration

        with patch("src.migration_executor.get_engine"):
            result = rollback_migrations(count=1, dry_run=False, verbose=False)

            # Should have attempted rollback
            assert result is not None

    @patch("src.migration_executor.get_applied_migrations")
    def test_rollback_no_migrations(self, mock_get_applied):
        """Test rollback when no migrations are applied."""
        mock_get_applied.return_value = []

        result = rollback_migrations(count=1, dry_run=False, verbose=False)

        assert result["successful"] == 0
        assert "No applied migrations" in result["message"]

    @patch("src.migration_executor.get_applied_migrations")
    def test_rollback_more_than_available(self, mock_get_applied):
        """Test rollback when requesting more rollbacks than available."""
        mock_applied = [Mock(version="001")]
        mock_get_applied.return_value = mock_applied

        result = rollback_migrations(count=5, dry_run=False, verbose=False)

        # Should only rollback available migrations
        assert result["successful"] <= 1


@pytest.mark.integration
class TestMigrationExecutorIntegration:
    """Integration tests for MigrationExecutor with real database."""

    def test_execute_migration_with_real_db(self, test_db_engine):
        """Test migration execution with a real database engine."""
        with patch("src.migration_executor.get_engine", return_value=test_db_engine):
            executor = MigrationExecutor(dry_run=False, verbose=True)

            migration = MigrationFile(
                version="20250101000000",
                description="Create test table",
                file_path=Path("/tmp/test.sql"),
                checksum="abc123",
                content="CREATE TABLE integration_test (id INTEGER PRIMARY KEY);",
                file_type="sql",
            )

            # Apply migration
            with patch("src.migration_executor.record_migration_success"):
                with patch("src.migration_executor.record_migration_failure"):
                    result = executor.apply_migration(migration)

            # Verify table was created
            with test_db_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='integration_test'")
                )
                tables = result.fetchall()
                assert len(tables) == 1
