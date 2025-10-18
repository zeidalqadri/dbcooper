import sys
from datetime import datetime

import click

from . import database, migration_manager
from .ai_generator import generate_migration_with_ai, get_ai_generator
from .compliance_checker import ComplianceChecker, check_compliance
from .migration_executor import apply_pending_migrations, rollback_migrations
from .migration_loader import create_migration_file, scan_migration_files
from .migration_state import get_applied_migrations, get_migration_state_report, get_pending_migrations
from .schema_interceptor import disable_schema_interception, enable_schema_interception


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """
    Database Migration Management System

    A comprehensive tool for managing database schema migrations with
    strict compliance enforcement and automated validation.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the database with migration tracking tables."""
    verbose = ctx.obj.get("verbose", False)
    click.echo("Initializing database...")

    try:
        migration_manager.initialize_db()
        click.echo("✓ Database initialized successfully")

        # Optionally install DDL triggers
        if click.confirm("Install DDL triggers for schema interception?", default=True):
            click.echo("Installing DDL triggers...")
            from .migration_executor import MigrationExecutor
            from .migration_loader import get_migration_by_version

            # Load and execute the trigger setup migration
            trigger_migration = get_migration_by_version("00000000000000")
            if trigger_migration:
                executor = MigrationExecutor(verbose=verbose)
                success, exec_time, error = executor.execute_migration(trigger_migration)

                if success:
                    click.echo(f"✓ DDL triggers installed successfully ({exec_time:.2f}s)")
                else:
                    click.echo(f"✗ Failed to install DDL triggers: {error}", err=True)
            else:
                click.echo("Warning: DDL trigger migration file not found", err=True)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="connect-test")
def connect_test():
    """Test the database connection."""
    click.echo("Testing database connection...")
    try:
        database.check_connection()
        click.echo("✓ Connection successful")
    except Exception as e:
        click.echo(f"✗ Connection test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("description")
@click.option("--sql", "file_type", flag_value="sql", default=True, help="Create SQL migration (default)")
@click.option("--py", "file_type", flag_value="py", help="Create Python migration")
def create(description, file_type):
    """
    Create a new migration file with timestamp.

    DESCRIPTION: Brief description of the migration (e.g., "create_users_table")
    """
    try:
        file_path = create_migration_file(description, file_type=file_type)
        click.echo(f"✓ Created migration: {file_path.name}")
        click.echo(f"  Path: {file_path}")
        click.echo(f"\nEdit the migration file and run 'apply' to execute it.")
    except Exception as e:
        click.echo(f"✗ Error creating migration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("prompt", required=False)
@click.option("--sql", "file_type", flag_value="sql", default=True, help="Generate SQL migration (default)")
@click.option("--py", "file_type", flag_value="py", help="Generate Python migration")
@click.option("--no-context", is_flag=True, help="Skip database schema context")
@click.option("--apply", "auto_apply", is_flag=True, help="Automatically apply after generation")
@click.pass_context
def generate(ctx, prompt, file_type, no_context, auto_apply):
    """
    Generate migration using AI from natural language.

    PROMPT: Natural language description (e.g., "Add email column to users")

    Examples:
      python -m src.cli generate "Add email to users"
      python -m src.cli generate "Create posts table with user relationship"
      python -m src.cli generate --apply "Add index on users.email"
    """
    verbose = ctx.obj.get("verbose", False)

    try:
        # Check if AI is available
        generator = get_ai_generator()
        if not generator.is_available():
            available = generator.get_available_providers()
            click.echo("✗ AI generation not available", err=True)
            click.echo("\nNo API keys configured.", err=True)
            if available:
                click.echo(f"Available providers: {', '.join(available)}", err=True)
            else:
                click.echo("Configure an AI provider:", err=True)
                click.echo("  export OPENAI_API_KEY=your_key", err=True)
                click.echo("  or", err=True)
                click.echo("  export ANTHROPIC_API_KEY=your_key", err=True)
            sys.exit(1)

        # Get prompt interactively if not provided
        if not prompt:
            click.echo("AI Migration Generator")
            click.echo("=" * 50)
            prompt = click.prompt("\nDescribe your migration")

        click.echo(f"\nGenerating migration with AI... ", nl=False)

        # Generate migration
        result = generate_migration_with_ai(prompt=prompt, file_type=file_type, include_context=not no_context)

        click.echo("✓")

        # Display results
        click.echo("\n" + "=" * 70)
        click.echo("GENERATED MIGRATION")
        click.echo("=" * 70)
        click.echo(f"\nDescription: {result.description}")
        click.echo(f"Confidence: {result.confidence:.0%}")

        if result.warnings:
            click.echo("\n⚠ Warnings:")
            for warning in result.warnings:
                click.echo(f"  - {warning}")

        if result.suggestions:
            click.echo("\n💡 Suggestions:")
            for suggestion in result.suggestions:
                click.echo(f"  - {suggestion}")

        if result.reasoning and verbose:
            click.echo(f"\n🧠 Reasoning: {result.reasoning}")

        click.echo("\n" + "-" * 70)
        click.echo("Generated SQL:")
        click.echo("-" * 70)
        click.echo(result.sql)
        click.echo("-" * 70)

        if result.rollback_sql:
            click.echo("\nRollback SQL:")
            click.echo("-" * 70)
            click.echo(result.rollback_sql)
            click.echo("-" * 70)

        # Save migration
        if result.confidence > 0.0:
            if auto_apply or click.confirm("\nSave this migration?"):
                file_path = create_migration_file(
                    description=result.description, content=result.sql, file_type=file_type
                )
                click.echo(f"\n✓ Saved: {file_path.name}")
                click.echo(f"  Path: {file_path}")

                # Auto-apply if requested
                if auto_apply:
                    if click.confirm("\nApply migration now?"):
                        ctx.invoke(apply, dry_run=False)
            else:
                click.echo("\nMigration not saved")
        else:
            click.echo("\n✗ Migration generation failed - not saving")
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show current migration status and compliance state."""
    verbose = ctx.obj.get("verbose", False)

    try:
        state_report = get_migration_state_report()

        click.echo("\n" + "=" * 70)
        click.echo("MIGRATION STATUS")
        click.echo("=" * 70)

        # Summary
        click.echo(f"\nApplied migrations:  {state_report.applied_count}")
        click.echo(f"Pending migrations:  {state_report.pending_count}")
        click.echo(f"Failed migrations:   {state_report.failed_count}")

        if state_report.last_applied_version:
            click.echo(f"Last applied:        {state_report.last_applied_version}")
            click.echo(f"                     ({state_report.last_applied_timestamp.isoformat()})")
        else:
            click.echo("Last applied:        None")

        # Compliance status
        click.echo(f"\nCompliance status:   {'✓ COMPLIANT' if state_report.is_compliant else '✗ VIOLATIONS DETECTED'}")

        # Pending migrations
        if state_report.pending_migrations:
            click.echo(f"\nPending migrations ({len(state_report.pending_migrations)}):")
            for pm in state_report.pending_migrations[:10]:  # Show first 10
                click.echo(f"  - {pm.version}: {pm.description}")
            if len(state_report.pending_migrations) > 10:
                click.echo(f"  ... and {len(state_report.pending_migrations) - 10} more")

        # Recent applied migrations
        if state_report.applied_migrations and verbose:
            click.echo(f"\nRecent applied migrations:")
            for am in state_report.applied_migrations[:5]:
                status_icon = "✓" if am.is_successful else "✗"
                click.echo(f"  {status_icon} {am.version}: {am.description}")
                click.echo(f"     Applied: {am.applied_at.isoformat()}, Time: {am.execution_time:.2f}s")

        # Warnings
        if state_report.checksum_mismatches:
            click.echo(f"\n⚠ WARNING: {len(state_report.checksum_mismatches)} checksum mismatch(es) detected!")

        if state_report.orphaned_migrations:
            click.echo(f"\n⚠ WARNING: {len(state_report.orphaned_migrations)} orphaned migration(s)!")

        click.echo("\n" + "=" * 70)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--dry-run", is_flag=True, help="Validate without executing")
@click.pass_context
def apply(ctx, dry_run):
    """Apply all pending migrations sequentially."""
    verbose = ctx.obj.get("verbose", False)

    if dry_run:
        click.echo("DRY RUN MODE - No changes will be made")

    click.echo("Applying pending migrations...")

    try:
        successful, failed, errors = apply_pending_migrations(dry_run=dry_run, verbose=verbose)

        click.echo(f"\n{'='*70}")
        click.echo(f"Migration execution complete:")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed:     {failed}")

        if errors:
            click.echo(f"\nErrors:")
            for error in errors:
                click.echo(f"  ✗ {error}")
            sys.exit(1)
        else:
            click.echo(f"\n✓ All migrations applied successfully")

    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("count", type=int, default=1)
@click.option("--dry-run", is_flag=True, help="Validate without executing")
@click.pass_context
def rollback(ctx, count, dry_run):
    """
    Rollback the last N migrations.

    COUNT: Number of migrations to rollback (default: 1)
    """
    verbose = ctx.obj.get("verbose", False)

    if dry_run:
        click.echo("DRY RUN MODE - No changes will be made")

    if not click.confirm(f"Rollback last {count} migration(s)?", default=False):
        click.echo("Cancelled")
        return

    try:
        successful, failed, errors = rollback_migrations(count, dry_run=dry_run, verbose=verbose)

        click.echo(f"\n{'='*70}")
        click.echo(f"Rollback complete:")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed:     {failed}")

        if errors:
            click.echo(f"\nErrors:")
            for error in errors:
                click.echo(f"  ✗ {error}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def validate():
    """Run compliance validation checks without applying migrations."""
    click.echo("Running compliance validation...\n")

    try:
        checker = ComplianceChecker(verbose=True)
        report = checker.check_compliance()

        click.echo(checker.generate_compliance_summary())

        if not report.is_compliant:
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--limit", "-n", type=int, default=20, help="Number of migrations to show")
def history(limit):
    """Show migration history."""
    try:
        applied = get_applied_migrations()

        if not applied:
            click.echo("No migrations have been applied yet")
            return

        click.echo(f"\n{'='*70}")
        click.echo("MIGRATION HISTORY")
        click.echo(f"{'='*70}\n")

        for migration in applied[:limit]:
            status_icon = "✓" if migration.is_successful else "✗"
            click.echo(f"{status_icon} {migration.version}: {migration.description}")
            click.echo(f"   Applied: {migration.applied_at.isoformat()}")
            click.echo(f"   Status: {migration.status}")
            click.echo(f"   Time: {migration.execution_time:.2f}s" if migration.execution_time else "   Time: N/A")

            if migration.is_failed and migration.error_message:
                click.echo(f"   Error: {migration.error_message[:100]}...")
            click.echo()

        if len(applied) > limit:
            click.echo(f"... and {len(applied) - limit} more (use --limit to show more)")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def repair():
    """Repair migration issues (remove failed migration records)."""
    click.echo("Checking for failed migrations...")

    try:
        from .migration_state import delete_migration_record

        applied = get_applied_migrations()
        failed = [m for m in applied if m.is_failed]

        if not failed:
            click.echo("✓ No failed migrations found")
            return

        click.echo(f"\nFound {len(failed)} failed migration(s):")
        for migration in failed:
            click.echo(f"  - {migration.version}: {migration.description}")

        if click.confirm("\nRemove these failed migration records?", default=False):
            for migration in failed:
                delete_migration_record(migration.version)
                click.echo(f"✓ Removed: {migration.version}")

            click.echo(f"\n✓ Repaired {len(failed)} failed migration(s)")
            click.echo("You can now retry applying these migrations.")
        else:
            click.echo("Cancelled")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def list():
    """List all available migration files."""
    try:
        migrations = scan_migration_files()

        if not migrations:
            click.echo("No migration files found in migrations/ directory")
            return

        click.echo(f"\n{'='*70}")
        click.echo(f"AVAILABLE MIGRATIONS ({len(migrations)})")
        click.echo(f"{'='*70}\n")

        # Get applied migrations
        applied = get_applied_migrations()
        applied_versions = {m.version for m in applied}

        for migration in migrations:
            status = "✓ Applied" if migration.version in applied_versions else "○ Pending"
            click.echo(f"{status}  {migration.version}: {migration.description}")
            click.echo(f"          File: {migration.file_path.name}")
            click.echo(f"          Checksum: {migration.checksum[:16]}...")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--enable", is_flag=True, help="Enable schema interception")
@click.option("--disable", is_flag=True, help="Disable schema interception")
def interceptor(enable, disable):
    """Manage the schema modification interceptor."""
    if enable and disable:
        click.echo("Error: Cannot specify both --enable and --disable", err=True)
        sys.exit(1)

    if enable:
        try:
            enable_schema_interception(strict_mode=True)
            click.echo("✓ Schema interceptor ENABLED")
            click.echo("  All DDL statements will be validated for migration compliance")
        except Exception as e:
            click.echo(f"✗ Error: {e}", err=True)
            sys.exit(1)

    elif disable:
        try:
            disable_schema_interception()
            click.echo("✓ Schema interceptor DISABLED")
            click.echo("  DDL statements will not be validated")
        except Exception as e:
            click.echo(f"✗ Error: {e}", err=True)
            sys.exit(1)

    else:
        click.echo("Usage: python -m src.cli interceptor --enable | --disable")


if __name__ == "__main__":
    cli(obj={})
