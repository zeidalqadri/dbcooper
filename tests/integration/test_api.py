"""
Integration tests for FastAPI endpoints.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    # Import here to avoid circular imports
    with patch("src.api.get_engine"):
        from src.api import app

        return TestClient(app)


@pytest.fixture
def mock_migration_state():
    """Mock migration state responses."""
    from src.migration_state import MigrationStateReport

    return MigrationStateReport(
        applied_count=5,
        pending_count=2,
        failed_count=0,
        last_applied_version="20250101000000",
        last_applied_timestamp=datetime.now(),
        checksum_mismatches=[],
        is_clean=True,
    )


@pytest.mark.integration
class TestHealthEndpoint:
    """Test /health endpoint."""

    @patch("src.api.check_connection")
    def test_health_endpoint_success(self, mock_check, test_client):
        """Test health endpoint returns success when DB is connected."""
        mock_check.return_value = True

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True

    @patch("src.api.check_connection")
    def test_health_endpoint_db_down(self, mock_check, test_client):
        """Test health endpoint when database is down."""
        mock_check.return_value = False

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["database_connected"] is False


@pytest.mark.integration
class TestMigrationStatusEndpoint:
    """Test /api/migrations/status endpoint."""

    @patch("src.api.get_migration_state_report")
    def test_migration_status_success(self, mock_state, test_client, mock_migration_state):
        """Test getting migration status."""
        mock_state.return_value = mock_migration_state

        response = test_client.get("/api/migrations/status")

        assert response.status_code == 200
        data = response.json()
        assert data["applied_count"] == 5
        assert data["pending_count"] == 2
        assert data["failed_count"] == 0
        assert data["is_compliant"] is True


@pytest.mark.integration
class TestAppliedMigrationsEndpoint:
    """Test /api/migrations/applied endpoint."""

    @patch("src.api.get_applied_migrations")
    def test_get_applied_migrations(self, mock_get_applied, test_client):
        """Test getting list of applied migrations."""
        from src.migration_state import AppliedMigration

        mock_migrations = [
            AppliedMigration(
                version="20250101000000",
                description="Initial schema",
                applied_at=datetime.now(),
                checksum="abc123",
                status="success",
                execution_time=0.5,
                error_message=None,
            )
        ]
        mock_get_applied.return_value = mock_migrations

        response = test_client.get("/api/migrations/applied")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version"] == "20250101000000"
        assert data[0]["status"] == "success"


@pytest.mark.integration
class TestPendingMigrationsEndpoint:
    """Test /api/migrations/pending endpoint."""

    @patch("src.api.get_pending_migrations")
    def test_get_pending_migrations(self, mock_get_pending, test_client):
        """Test getting list of pending migrations."""
        from src.migration_state import PendingMigration

        mock_migrations = [
            PendingMigration(
                version="20250101000001",
                description="Add users table",
                file_path="/path/to/migration.sql",
                checksum="def456",
                file_type="sql",
            )
        ]
        mock_get_pending.return_value = mock_migrations

        response = test_client.get("/api/migrations/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version"] == "20250101000001"
        assert data[0]["file_type"] == "sql"


@pytest.mark.integration
class TestApplyMigrationsEndpoint:
    """Test /api/migrations/apply endpoint."""

    @patch("src.api.apply_pending_migrations")
    def test_apply_migrations_success(self, mock_apply, test_client):
        """Test applying migrations successfully."""
        mock_apply.return_value = {
            "successful": 2,
            "failed": 0,
            "errors": [],
            "message": "Successfully applied 2 migrations",
        }

        response = test_client.post("/api/migrations/apply", json={"dry_run": False, "verbose": False})

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2
        assert data["failed"] == 0

    @patch("src.api.apply_pending_migrations")
    def test_apply_migrations_with_failures(self, mock_apply, test_client):
        """Test applying migrations with some failures."""
        mock_apply.return_value = {
            "successful": 1,
            "failed": 1,
            "errors": ["Migration 002 failed"],
            "message": "Applied 1/2 migrations",
        }

        response = test_client.post("/api/migrations/apply", json={"dry_run": False, "verbose": True})

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1
        assert len(data["errors"]) == 1

    @patch("src.api.apply_pending_migrations")
    def test_apply_migrations_dry_run(self, mock_apply, test_client):
        """Test applying migrations in dry-run mode."""
        mock_apply.return_value = {
            "successful": 0,
            "failed": 0,
            "errors": [],
            "message": "Dry run: would apply 2 migrations",
        }

        response = test_client.post("/api/migrations/apply", json={"dry_run": True, "verbose": False})

        assert response.status_code == 200
        data = response.json()
        mock_apply.assert_called_once_with(dry_run=True, verbose=False)


@pytest.mark.integration
class TestRollbackEndpoint:
    """Test /api/migrations/rollback endpoint."""

    @patch("src.api.rollback_migrations")
    def test_rollback_success(self, mock_rollback, test_client):
        """Test rolling back migrations."""
        mock_rollback.return_value = {
            "successful": 1,
            "failed": 0,
            "errors": [],
            "message": "Successfully rolled back 1 migration",
        }

        response = test_client.post("/api/migrations/rollback", json={"count": 1, "dry_run": False})

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1

    @patch("src.api.rollback_migrations")
    def test_rollback_validation_error(self, mock_rollback, test_client):
        """Test rollback with invalid count."""
        response = test_client.post("/api/migrations/rollback", json={"count": 0, "dry_run": False})

        # Should fail validation (count must be >= 1)
        assert response.status_code == 422


@pytest.mark.integration
class TestComplianceEndpoint:
    """Test /api/compliance/check endpoint."""

    @patch("src.api.check_compliance")
    def test_compliance_check_compliant(self, mock_check, test_client):
        """Test compliance check when compliant."""
        from src.compliance_checker import ComplianceReport
        from src.migration_state import MigrationStateReport

        mock_report = ComplianceReport(
            is_compliant=True,
            timestamp=datetime.now(),
            violations=[],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )
        mock_check.return_value = mock_report

        response = test_client.get("/api/compliance/check")

        assert response.status_code == 200
        data = response.json()
        assert data["is_compliant"] is True
        assert data["violation_count"] == 0

    @patch("src.api.check_compliance")
    def test_compliance_check_violations(self, mock_check, test_client):
        """Test compliance check with violations."""
        from src.compliance_checker import ComplianceReport, ComplianceViolation
        from src.migration_state import MigrationStateReport

        violation = ComplianceViolation(
            severity="critical", category="pending_migrations", message="3 pending migrations", details={"count": 3}
        )

        mock_report = ComplianceReport(
            is_compliant=False,
            timestamp=datetime.now(),
            violations=[violation],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=["Apply pending migrations"],
        )
        mock_check.return_value = mock_report

        response = test_client.get("/api/compliance/check")

        assert response.status_code == 200
        data = response.json()
        assert data["is_compliant"] is False
        assert data["violation_count"] == 1
        assert len(data["violations"]) == 1


@pytest.mark.integration
class TestCreateMigrationEndpoint:
    """Test /api/migrations/create endpoint."""

    @patch("src.api.create_migration_file")
    def test_create_migration_success(self, mock_create, test_client):
        """Test creating a new migration."""
        from src.migration_loader import MigrationFile

        mock_migration = MigrationFile(
            version="20250101000002",
            description="Add users table",
            file_path="/path/to/migration.sql",
            checksum="abc123",
            content="",
            file_type="sql",
        )
        mock_create.return_value = mock_migration

        response = test_client.post(
            "/api/migrations/create", json={"description": "Add users table", "file_type": "sql"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version"] == "20250101000002"
        assert data["description"] == "Add users table"

    def test_create_migration_invalid_input(self, test_client):
        """Test creating migration with invalid input."""
        response = test_client.post("/api/migrations/create", json={"description": "", "file_type": "sql"})

        # Should fail validation (description too short)
        assert response.status_code == 422

    def test_create_migration_invalid_file_type(self, test_client):
        """Test creating migration with invalid file type."""
        response = test_client.post("/api/migrations/create", json={"description": "Test", "file_type": "txt"})

        # Should fail validation (invalid file type)
        assert response.status_code == 422


@pytest.mark.integration
class TestScanMigrationsEndpoint:
    """Test /api/migrations/scan endpoint."""

    @patch("src.api.scan_migration_files")
    def test_scan_migrations(self, mock_scan, test_client):
        """Test scanning migration files."""
        from src.migration_loader import MigrationFile

        mock_migrations = [
            MigrationFile(
                version="20250101000000",
                description="Initial",
                file_path="/path/to/migration.sql",
                checksum="abc",
                content="",
                file_type="sql",
            )
        ]
        mock_scan.return_value = mock_migrations

        response = test_client.post("/api/migrations/scan")

        assert response.status_code == 200
        data = response.json()
        assert data["scanned_count"] == 1
        assert len(data["migrations"]) == 1


@pytest.mark.integration
class TestAIGenerationEndpoint:
    """Test /api/ai/generate endpoint."""

    @patch("src.api.generate_migration_with_ai")
    def test_ai_generate_migration_success(self, mock_generate, test_client):
        """Test AI migration generation."""
        from src.ai_providers import GeneratedMigration

        mock_result = GeneratedMigration(
            sql_content="CREATE TABLE users (id INT);",
            description="Add users table",
            confidence=0.95,
            provider="openai",
            model="gpt-4",
            tokens_used=150,
        )
        mock_generate.return_value = mock_result

        response = test_client.post(
            "/api/ai/generate",
            json={"prompt": "Create a users table", "context": "PostgreSQL database", "provider": "openai"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sql_content" in data

    @patch("src.api.generate_migration_with_ai")
    def test_ai_generate_migration_failure(self, mock_generate, test_client):
        """Test AI migration generation failure."""
        mock_generate.side_effect = Exception("AI service unavailable")

        response = test_client.post("/api/ai/generate", json={"prompt": "Create a users table", "provider": "openai"})

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "error" in data


@pytest.mark.integration
class TestWebSocketEndpoint:
    """Test WebSocket endpoint."""

    @pytest.mark.skip(reason="WebSocket testing requires special setup")
    def test_websocket_connection(self, test_client):
        """Test WebSocket connection for real-time updates."""
        # WebSocket testing would require more complex setup
        # This is a placeholder for future implementation
        pass


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""

    def test_404_not_found(self, test_client):
        """Test 404 error for non-existent endpoint."""
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404

    @patch("src.api.get_migration_state_report")
    def test_500_internal_error(self, mock_state, test_client):
        """Test 500 error handling."""
        mock_state.side_effect = Exception("Database connection failed")

        response = test_client.get("/api/migrations/status")

        # Should handle internal errors gracefully
        assert response.status_code in [500, 503]
