from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import get_engine
from .migration_state import MigrationStateReport, get_applied_migrations, get_migration_state_report, table_exists


@dataclass
class ComplianceViolation:
    """Represents a single compliance violation."""

    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'pending_migrations', 'checksum_mismatch', 'failed_migration', etc.
    message: str
    details: Dict[str, Any]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.category}: {self.message}"


@dataclass
class ComplianceReport:
    """Comprehensive compliance report with violations and recommendations."""

    is_compliant: bool
    timestamp: datetime
    violations: List[ComplianceViolation]
    state_report: MigrationStateReport
    recommendations: List[str]

    @property
    def critical_violations(self) -> List[ComplianceViolation]:
        return [v for v in self.violations if v.severity == "critical"]

    @property
    def has_critical_violations(self) -> bool:
        return len(self.critical_violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)


class ComplianceViolationError(Exception):
    """Exception raised when compliance violations block an operation."""

    def __init__(self, message: str, violations: List[ComplianceViolation]):
        super().__init__(message)
        self.violations = violations


class ComplianceChecker:
    """Audits and enforces migration compliance."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the compliance checker.

        Args:
            verbose: If True, print detailed information
        """
        self.verbose = verbose
        self.engine = get_engine()

    def _log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[COMPLIANCE] {message}")

    def audit_migration_state(self) -> MigrationStateReport:
        """
        Execute Migration Audit Sequence:
        1. Query all applied migrations from schema_migrations
        2. Validate migration table exists
        3. Cross-reference with migration files
        4. Generate comprehensive state report

        Returns:
            MigrationStateReport with full state analysis
        """
        self._log("Starting migration audit sequence...")

        # Check if schema_migrations table exists
        if not table_exists(self.engine):
            self._log("WARNING: schema_migrations table does not exist!")
            # Return empty report
            from .migration_state import MigrationStateReport

            return MigrationStateReport(
                applied_count=0,
                pending_count=0,
                failed_count=0,
                last_applied_version=None,
                last_applied_timestamp=None,
                applied_migrations=[],
                pending_migrations=[],
                checksum_mismatches=[],
                orphaned_migrations=[],
            )

        # Get comprehensive state report
        state_report = get_migration_state_report()

        self._log(
            f"Audit complete: {state_report.applied_count} applied, "
            f"{state_report.pending_count} pending, "
            f"{state_report.failed_count} failed"
        )

        return state_report

    def check_compliance(self) -> ComplianceReport:
        """
        Execute comprehensive compliance check.

        Returns:
            ComplianceReport with all violations and recommendations
        """
        self._log("Executing compliance check...")

        violations = []
        recommendations = []

        # Get migration state
        state_report = self.audit_migration_state()

        # Check 1: Pending migrations (CRITICAL)
        if state_report.has_pending:
            violations.append(
                ComplianceViolation(
                    severity="critical",
                    category="pending_migrations",
                    message=f"{state_report.pending_count} pending migration(s) must be applied before schema modifications",
                    details={
                        "pending_count": state_report.pending_count,
                        "pending_versions": [m.version for m in state_report.pending_migrations],
                    },
                )
            )
            recommendations.append(
                f"Apply {state_report.pending_count} pending migration(s) using: python -m src.cli apply"
            )

        # Check 2: Failed migrations (CRITICAL)
        if state_report.has_failed:
            violations.append(
                ComplianceViolation(
                    severity="critical",
                    category="failed_migrations",
                    message=f"{state_report.failed_count} migration(s) failed during execution",
                    details={
                        "failed_count": state_report.failed_count,
                        "failed_versions": [m.version for m in state_report.applied_migrations if m.is_failed],
                    },
                )
            )
            recommendations.append(
                "Review and fix failed migrations, then remove failed records using: python -m src.cli repair"
            )

        # Check 3: Checksum mismatches (HIGH)
        if state_report.has_checksum_mismatches:
            violations.append(
                ComplianceViolation(
                    severity="high",
                    category="checksum_mismatch",
                    message=f"{len(state_report.checksum_mismatches)} migration file(s) modified after application (checksum mismatch)",
                    details={
                        "mismatch_count": len(state_report.checksum_mismatches),
                        "mismatches": state_report.checksum_mismatches,
                    },
                )
            )
            recommendations.append(
                "Migration files should never be modified after application. Review changes and create new migrations instead."
            )

        # Check 4: Orphaned migrations (MEDIUM)
        if state_report.has_orphaned:
            violations.append(
                ComplianceViolation(
                    severity="medium",
                    category="orphaned_migrations",
                    message=f"{len(state_report.orphaned_migrations)} migration(s) in database but files not found",
                    details={
                        "orphaned_count": len(state_report.orphaned_migrations),
                        "orphaned_versions": [m.version for m in state_report.orphaned_migrations],
                    },
                )
            )
            recommendations.append("Restore missing migration files or clean up orphaned records.")

        # Check 5: Schema migrations table exists
        if not table_exists(self.engine):
            violations.append(
                ComplianceViolation(
                    severity="critical",
                    category="missing_schema_table",
                    message="schema_migrations table does not exist",
                    details={"table_name": "schema_migrations"},
                )
            )
            recommendations.append("Initialize the database using: python -m src.cli init")

        # Determine overall compliance
        is_compliant = len(violations) == 0

        report = ComplianceReport(
            is_compliant=is_compliant,
            timestamp=datetime.utcnow(),
            violations=violations,
            state_report=state_report,
            recommendations=recommendations,
        )

        self._log(f"Compliance check complete: {'COMPLIANT' if is_compliant else 'VIOLATIONS DETECTED'}")

        return report

    def enforce_compliance(self, operation: str = "schema modification") -> None:
        """
        Enforce migration compliance with BLOCKING behavior.
        Raises ComplianceViolationError if violations detected.

        Args:
            operation: Description of the operation being blocked

        Raises:
            ComplianceViolationError: If any compliance violations detected
        """
        self._log(f"Enforcing compliance for: {operation}")

        compliance_report = self.check_compliance()

        if not compliance_report.is_compliant:
            # Build error message
            error_lines = [
                f"MIGRATION_VIOLATION: {operation} blocked due to compliance violations",
                "",
                "Detected violations:",
            ]

            for violation in compliance_report.violations:
                error_lines.append(f"  - [{violation.severity.upper()}] {violation.message}")

            error_lines.append("")
            error_lines.append("Recommendations:")
            for rec in compliance_report.recommendations:
                error_lines.append(f"  - {rec}")

            error_message = "\n".join(error_lines)

            self._log("COMPLIANCE ENFORCEMENT FAILED - Blocking operation")

            raise ComplianceViolationError(error_message, compliance_report.violations)

        self._log("Compliance enforcement passed")

    def verify_checksums(self) -> bool:
        """
        Verify that all applied migration checksums match their file contents.

        Returns:
            True if all checksums match, False otherwise
        """
        self._log("Verifying migration checksums...")

        state_report = self.audit_migration_state()

        if state_report.has_checksum_mismatches:
            self._log(f"CHECKSUM VERIFICATION FAILED: {len(state_report.checksum_mismatches)} mismatch(es)")
            for mismatch in state_report.checksum_mismatches:
                self._log(f"  - {mismatch['version']}: file checksum != db checksum")
            return False

        self._log("Checksum verification passed")
        return True

    def verify_no_failed_migrations(self) -> bool:
        """
        Verify that there are no failed migration attempts in history.

        Returns:
            True if no failed migrations, False otherwise
        """
        self._log("Checking for failed migrations...")

        applied = get_applied_migrations()
        failed = [m for m in applied if m.is_failed]

        if failed:
            self._log(f"FAILED MIGRATION CHECK FAILED: {len(failed)} failed migration(s)")
            for migration in failed:
                self._log(
                    f"  - {migration.version}: {migration.error_message[:100] if migration.error_message else 'Unknown error'}"
                )
            return False

        self._log("No failed migrations found")
        return True

    def generate_compliance_summary(self) -> str:
        """
        Generate a human-readable compliance summary.

        Returns:
            Formatted compliance summary string
        """
        report = self.check_compliance()
        state = report.state_report

        lines = [
            "=" * 70,
            "MIGRATION COMPLIANCE REPORT",
            "=" * 70,
            f"Timestamp: {report.timestamp.isoformat()}",
            f"Status: {'✓ COMPLIANT' if report.is_compliant else '✗ VIOLATIONS DETECTED'}",
            "",
            "Migration State:",
            f"  Applied migrations: {state.applied_count}",
            f"  Pending migrations: {state.pending_count}",
            f"  Failed migrations: {state.failed_count}",
            f"  Last applied: {state.last_applied_version or 'None'} "
            f"({state.last_applied_timestamp.isoformat() if state.last_applied_timestamp else 'N/A'})",
            "",
        ]

        if report.violations:
            lines.append("Violations:")
            for violation in report.violations:
                lines.append(f"  [{violation.severity.upper()}] {violation.category}")
                lines.append(f"    {violation.message}")
            lines.append("")

        if report.recommendations:
            lines.append("Recommendations:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")
            lines.append("")

        if state.checksum_mismatches:
            lines.append("Checksum Mismatches:")
            for mismatch in state.checksum_mismatches:
                lines.append(f"  - {mismatch['version']}: {mismatch['description']}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def enforce_migration_compliance(operation: str = "schema modification") -> None:
    """
    Convenience function to enforce compliance.

    Args:
        operation: Description of the operation being enforced

    Raises:
        ComplianceViolationError: If compliance violations detected
    """
    checker = ComplianceChecker(verbose=True)
    checker.enforce_compliance(operation)


def check_compliance(verbose: bool = False) -> ComplianceReport:
    """
    Convenience function to check compliance.

    Args:
        verbose: If True, print detailed information

    Returns:
        ComplianceReport
    """
    checker = ComplianceChecker(verbose=verbose)
    return checker.check_compliance()
