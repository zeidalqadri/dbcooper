"""
Unit tests for compliance_checker module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.compliance_checker import (
    ComplianceChecker,
    ComplianceViolation,
    ComplianceReport,
    ComplianceViolationError,
    check_compliance,
)


@pytest.fixture
def compliance_checker():
    """Create a ComplianceChecker instance for testing."""
    with patch("src.compliance_checker.get_engine"):
        return ComplianceChecker(verbose=True)


@pytest.fixture
def sample_violation():
    """Create a sample compliance violation."""
    return ComplianceViolation(
        severity="critical", category="pending_migrations", message="Pending migrations detected", details={"count": 3}
    )


@pytest.fixture
def sample_compliance_report():
    """Create a sample compliance report."""
    from src.migration_state import MigrationStateReport

    state_report = MigrationStateReport(
        applied_count=5,
        pending_count=0,
        failed_count=0,
        last_applied_version="20250101000000",
        last_applied_timestamp=datetime.now(),
        checksum_mismatches=[],
        is_clean=True,
    )

    return ComplianceReport(
        is_compliant=True, timestamp=datetime.now(), violations=[], state_report=state_report, recommendations=[]
    )


class TestComplianceViolation:
    """Test ComplianceViolation dataclass."""

    def test_violation_creation(self, sample_violation):
        """Test creating a compliance violation."""
        assert sample_violation.severity == "critical"
        assert sample_violation.category == "pending_migrations"
        assert sample_violation.message == "Pending migrations detected"
        assert sample_violation.details["count"] == 3

    def test_violation_string_representation(self, sample_violation):
        """Test string representation of violation."""
        result = str(sample_violation)
        assert "CRITICAL" in result
        assert "pending_migrations" in result
        assert "Pending migrations detected" in result

    @pytest.mark.parametrize(
        "severity,expected",
        [
            ("critical", "CRITICAL"),
            ("high", "HIGH"),
            ("medium", "MEDIUM"),
            ("low", "LOW"),
        ],
    )
    def test_violation_severity_levels(self, severity, expected):
        """Test different severity levels."""
        violation = ComplianceViolation(severity=severity, category="test", message="test", details={})
        assert expected in str(violation)


class TestComplianceReport:
    """Test ComplianceReport dataclass."""

    def test_report_creation(self, sample_compliance_report):
        """Test creating a compliance report."""
        assert sample_compliance_report.is_compliant is True
        assert isinstance(sample_compliance_report.timestamp, datetime)
        assert len(sample_compliance_report.violations) == 0

    def test_critical_violations_property(self):
        """Test filtering critical violations."""
        from src.migration_state import MigrationStateReport

        violations = [
            ComplianceViolation("critical", "test1", "msg1", {}),
            ComplianceViolation("high", "test2", "msg2", {}),
            ComplianceViolation("critical", "test3", "msg3", {}),
        ]

        report = ComplianceReport(
            is_compliant=False,
            timestamp=datetime.now(),
            violations=violations,
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )

        assert len(report.critical_violations) == 2
        assert all(v.severity == "critical" for v in report.critical_violations)

    def test_has_critical_violations(self):
        """Test has_critical_violations property."""
        from src.migration_state import MigrationStateReport

        # With critical violations
        report_with_critical = ComplianceReport(
            is_compliant=False,
            timestamp=datetime.now(),
            violations=[ComplianceViolation("critical", "test", "msg", {})],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )
        assert report_with_critical.has_critical_violations is True

        # Without critical violations
        report_without_critical = ComplianceReport(
            is_compliant=True,
            timestamp=datetime.now(),
            violations=[ComplianceViolation("low", "test", "msg", {})],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )
        assert report_without_critical.has_critical_violations is False

    def test_violation_count_property(self):
        """Test violation_count property."""
        from src.migration_state import MigrationStateReport

        violations = [
            ComplianceViolation("critical", "test1", "msg1", {}),
            ComplianceViolation("high", "test2", "msg2", {}),
        ]

        report = ComplianceReport(
            is_compliant=False,
            timestamp=datetime.now(),
            violations=violations,
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )

        assert report.violation_count == 2


class TestComplianceViolationError:
    """Test ComplianceViolationError exception."""

    def test_exception_creation(self, sample_violation):
        """Test creating a compliance violation exception."""
        error = ComplianceViolationError("Compliance check failed", [sample_violation])

        assert str(error) == "Compliance check failed"
        assert len(error.violations) == 1
        assert error.violations[0] == sample_violation

    def test_exception_can_be_raised(self, sample_violation):
        """Test that exception can be raised and caught."""
        with pytest.raises(ComplianceViolationError) as exc_info:
            raise ComplianceViolationError("Test error", [sample_violation])

        assert len(exc_info.value.violations) == 1


class TestComplianceChecker:
    """Test ComplianceChecker class."""

    def test_initialization(self):
        """Test ComplianceChecker initialization."""
        with patch("src.compliance_checker.get_engine") as mock_engine:
            checker = ComplianceChecker(verbose=True)
            assert checker.verbose is True
            mock_engine.assert_called_once()

    def test_log_when_verbose(self, compliance_checker, capsys):
        """Test logging when verbose mode is enabled."""
        compliance_checker.verbose = True
        compliance_checker._log("Test message")
        captured = capsys.readouterr()
        assert "[COMPLIANCE] Test message" in captured.out

    def test_no_log_when_not_verbose(self, compliance_checker, capsys):
        """Test no logging when verbose mode is disabled."""
        compliance_checker.verbose = False
        compliance_checker._log("Test message")
        captured = capsys.readouterr()
        assert captured.out == ""

    @patch("src.compliance_checker.get_migration_state_report")
    def test_audit_migration_state(self, mock_state_report, compliance_checker):
        """Test migration state audit."""
        from src.migration_state import MigrationStateReport

        mock_report = MigrationStateReport(
            applied_count=5,
            pending_count=2,
            failed_count=0,
            last_applied_version="001",
            last_applied_timestamp=datetime.now(),
            checksum_mismatches=[],
            is_clean=True,
        )
        mock_state_report.return_value = mock_report

        result = compliance_checker.audit_migration_state()

        assert result == mock_report
        mock_state_report.assert_called_once()

    @patch("src.compliance_checker.get_migration_state_report")
    def test_check_pending_migrations_with_pending(self, mock_state_report, compliance_checker):
        """Test checking pending migrations when some exist."""
        from src.migration_state import MigrationStateReport

        mock_report = MigrationStateReport(
            applied_count=5,
            pending_count=3,
            failed_count=0,
            last_applied_version="001",
            last_applied_timestamp=datetime.now(),
            checksum_mismatches=[],
            is_clean=False,
        )

        violations = compliance_checker.check_pending_migrations(mock_report)

        assert len(violations) == 1
        assert violations[0].severity == "high"
        assert violations[0].category == "pending_migrations"

    @patch("src.compliance_checker.get_migration_state_report")
    def test_check_pending_migrations_without_pending(self, mock_state_report, compliance_checker):
        """Test checking pending migrations when none exist."""
        from src.migration_state import MigrationStateReport

        mock_report = MigrationStateReport(
            applied_count=5,
            pending_count=0,
            failed_count=0,
            last_applied_version="001",
            last_applied_timestamp=datetime.now(),
            checksum_mismatches=[],
            is_clean=True,
        )

        violations = compliance_checker.check_pending_migrations(mock_report)

        assert len(violations) == 0

    def test_check_sql_for_destructive_operations(self, compliance_checker):
        """Test detection of destructive SQL operations."""
        destructive_sql = """
        DROP TABLE users;
        TRUNCATE TABLE posts;
        DELETE FROM comments;
        """

        violations = compliance_checker.check_sql_for_destructive_operations(destructive_sql, "test_migration")

        assert len(violations) > 0
        assert any(v.category == "destructive_operation" for v in violations)

    def test_check_sql_safe_operations(self, compliance_checker):
        """Test that safe SQL operations don't trigger violations."""
        safe_sql = """
        CREATE TABLE users (id INT);
        ALTER TABLE users ADD COLUMN email VARCHAR(255);
        CREATE INDEX idx_users_email ON users(email);
        """

        violations = compliance_checker.check_sql_for_destructive_operations(safe_sql, "test_migration")

        # Should have no violations for safe operations
        assert len(violations) == 0

    @pytest.mark.parametrize(
        "sql,should_violate",
        [
            ("DROP TABLE users;", True),
            ("TRUNCATE TABLE posts;", True),
            ("DELETE FROM comments;", True),
            ("CREATE TABLE new_table (id INT);", False),
            ("ALTER TABLE users ADD COLUMN email TEXT;", False),
            ("INSERT INTO users VALUES (1, 'test');", False),
            ("UPDATE users SET name='test' WHERE id=1;", False),
        ],
    )
    def test_destructive_operation_detection(self, compliance_checker, sql, should_violate):
        """Test detection of various SQL operations."""
        violations = compliance_checker.check_sql_for_destructive_operations(sql, "test")

        if should_violate:
            assert len(violations) > 0
        else:
            assert len(violations) == 0

    @patch("src.compliance_checker.get_migration_state_report")
    def test_generate_compliance_report_compliant(self, mock_state_report, compliance_checker):
        """Test generating compliance report when compliant."""
        from src.migration_state import MigrationStateReport

        mock_report = MigrationStateReport(
            applied_count=5,
            pending_count=0,
            failed_count=0,
            last_applied_version="001",
            last_applied_timestamp=datetime.now(),
            checksum_mismatches=[],
            is_clean=True,
        )
        mock_state_report.return_value = mock_report

        report = compliance_checker.generate_compliance_report()

        assert isinstance(report, ComplianceReport)
        assert report.is_compliant is True
        assert len(report.violations) == 0

    @patch("src.compliance_checker.get_migration_state_report")
    def test_generate_compliance_report_non_compliant(self, mock_state_report, compliance_checker):
        """Test generating compliance report when non-compliant."""
        from src.migration_state import MigrationStateReport

        mock_report = MigrationStateReport(
            applied_count=5,
            pending_count=3,
            failed_count=1,
            last_applied_version="001",
            last_applied_timestamp=datetime.now(),
            checksum_mismatches=[],
            is_clean=False,
        )
        mock_state_report.return_value = mock_report

        report = compliance_checker.generate_compliance_report()

        assert isinstance(report, ComplianceReport)
        assert report.is_compliant is False
        assert len(report.violations) > 0


class TestCheckComplianceFunction:
    """Test the check_compliance convenience function."""

    @patch("src.compliance_checker.ComplianceChecker")
    def test_check_compliance_success(self, mock_checker_class):
        """Test check_compliance function when compliant."""
        from src.migration_state import MigrationStateReport

        mock_checker = Mock()
        mock_report = ComplianceReport(
            is_compliant=True,
            timestamp=datetime.now(),
            violations=[],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=[],
        )
        mock_checker.generate_compliance_report.return_value = mock_report
        mock_checker_class.return_value = mock_checker

        result = check_compliance(verbose=False)

        assert result == mock_report
        assert result.is_compliant is True

    @patch("src.compliance_checker.ComplianceChecker")
    def test_check_compliance_with_violations(self, mock_checker_class):
        """Test check_compliance function with violations."""
        from src.migration_state import MigrationStateReport

        violation = ComplianceViolation(severity="critical", category="test", message="test", details={})

        mock_checker = Mock()
        mock_report = ComplianceReport(
            is_compliant=False,
            timestamp=datetime.now(),
            violations=[violation],
            state_report=Mock(spec=MigrationStateReport),
            recommendations=["Fix the issues"],
        )
        mock_checker.generate_compliance_report.return_value = mock_report
        mock_checker_class.return_value = mock_checker

        result = check_compliance(verbose=False)

        assert result.is_compliant is False
        assert len(result.violations) == 1


@pytest.mark.integration
class TestComplianceCheckerIntegration:
    """Integration tests for ComplianceChecker with real database."""

    def test_compliance_check_with_real_db(self, test_db_engine):
        """Test compliance checking with a real database."""
        with patch("src.compliance_checker.get_engine", return_value=test_db_engine):
            with patch("src.compliance_checker.get_migration_state_report") as mock_state:
                from src.migration_state import MigrationStateReport

                mock_state.return_value = MigrationStateReport(
                    applied_count=0,
                    pending_count=0,
                    failed_count=0,
                    last_applied_version=None,
                    last_applied_timestamp=None,
                    checksum_mismatches=[],
                    is_clean=True,
                )

                checker = ComplianceChecker(verbose=True)
                report = checker.generate_compliance_report()

                assert isinstance(report, ComplianceReport)
