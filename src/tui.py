
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
from datetime import datetime
from typing import Optional

from .migration_state import get_migration_state_report, get_applied_migrations, get_pending_migrations
from .migration_executor import apply_pending_migrations
from .compliance_checker import check_compliance
from .migration_loader import create_migration_file
from .ai_generator import generate_migration_with_ai, get_ai_generator

console = Console()


class MigrationTUI:
    """Terminal User Interface for Database Migration Management"""

    def __init__(self):
        self.console = console
        self.running = True

    def clear(self):
        """Clear the console"""
        self.console.clear()

    def show_header(self):
        """Display the application header"""
        header = Text("DB MIGRATION MANAGER v1.0.0", style="bold cyan", justify="center")
        self.console.print(Panel(header, style="cyan"))

    def show_status(self):
        """Display current migration status"""
        try:
            state = get_migration_state_report()

            # Create status table
            table = Table(title="Migration Status", show_header=False, box=None)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="bold")

            # Compliance status
            compliance_icon = "✓" if state.is_compliant else "✗"
            compliance_style = "green" if state.is_compliant else "red"

            table.add_row("Status", f"[{compliance_style}]{compliance_icon} {'COMPLIANT' if state.is_compliant else 'VIOLATIONS'}[/{compliance_style}]")
            table.add_row("Applied Migrations", str(state.applied_count))
            table.add_row("Pending Migrations", f"[yellow]{state.pending_count}[/yellow]" if state.pending_count > 0 else "0")
            table.add_row("Failed Migrations", f"[red]{state.failed_count}[/red]" if state.failed_count > 0 else "0")

            if state.last_applied_version:
                table.add_row("Last Applied", state.last_applied_version)
                table.add_row("Last Applied Time", state.last_applied_timestamp.strftime("%Y-%m-%d %H:%M:%S"))

            self.console.print(table)

            # Warnings
            if state.has_pending:
                self.console.print(f"\n[yellow]⚠ {state.pending_count} pending migration(s) need to be applied[/yellow]")
            if state.has_failed:
                self.console.print(f"[red]✗ {state.failed_count} failed migration(s) need attention[/red]")
            if state.has_checksum_mismatches:
                self.console.print(f"[red]⚠ Checksum mismatches detected![/red]")

        except Exception as e:
            self.console.print(f"[red]Error fetching status: {e}[/red]")

    def show_migrations(self):
        """Display migrations list"""
        try:
            applied = get_applied_migrations()
            pending = get_pending_migrations()

            # Pending migrations
            if pending:
                table = Table(title="[yellow]Pending Migrations[/yellow]", show_header=True)
                table.add_column("Version", style="cyan")
                table.add_column("Description")
                table.add_column("Type", style="magenta")

                for mig in pending:
                    table.add_row(mig.version, mig.description, mig.file_type.upper())

                self.console.print(table)

            # Recent applied migrations
            if applied:
                table = Table(title="\nRecent Applied Migrations", show_header=True)
                table.add_column("Status", width=6)
                table.add_column("Version", style="cyan")
                table.add_column("Description")
                table.add_column("Time", style="green")

                for mig in applied[:10]:
                    status_icon = "✓" if mig.is_successful else "✗"
                    status_style = "green" if mig.is_successful else "red"
                    exec_time = f"{mig.execution_time:.2f}s" if mig.execution_time else "N/A"

                    table.add_row(
                        f"[{status_style}]{status_icon}[/{status_style}]",
                        mig.version,
                        mig.description,
                        exec_time
                    )

                self.console.print(table)

        except Exception as e:
            self.console.print(f"[red]Error listing migrations: {e}[/red]")

    def show_compliance(self):
        """Display compliance report"""
        try:
            report = check_compliance()

            # Compliance status
            if report.is_compliant:
                self.console.print(Panel("[green]✓ COMPLIANT[/green]", title="Compliance Status"))
            else:
                self.console.print(Panel(f"[red]✗ {report.violation_count} VIOLATION(S)[/red]", title="Compliance Status"))

            # Violations
            if report.violations:
                table = Table(title="Violations", show_header=True)
                table.add_column("Severity", style="red")
                table.add_column("Category")
                table.add_column("Message")

                for violation in report.violations:
                    severity_colors = {
                        'critical': 'red',
                        'high': 'orange1',
                        'medium': 'yellow',
                        'low': 'cyan'
                    }
                    color = severity_colors.get(violation.severity, 'white')
                    table.add_row(
                        f"[{color}]{violation.severity.upper()}[/{color}]",
                        violation.category,
                        violation.message
                    )

                self.console.print(table)

            # Recommendations
            if report.recommendations:
                self.console.print("\n[bold]Recommendations:[/bold]")
                for i, rec in enumerate(report.recommendations, 1):
                    self.console.print(f"  {i}. {rec}")

        except Exception as e:
            self.console.print(f"[red]Error checking compliance: {e}[/red]")

    def apply_migrations_interactive(self):
        """Interactively apply pending migrations"""
        try:
            pending = get_pending_migrations()

            if not pending:
                self.console.print("[green]No pending migrations to apply[/green]")
                Prompt.ask("\nPress Enter to continue")
                return

            self.console.print(f"\n[yellow]Found {len(pending)} pending migration(s)[/yellow]")

            for mig in pending:
                self.console.print(f"  - {mig.version}: {mig.description}")

            if not Confirm.ask("\nProceed with applying migrations?"):
                self.console.print("[yellow]Cancelled[/yellow]")
                return

            # Apply migrations with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Applying migrations...", total=len(pending))

                successful, failed, errors = apply_pending_migrations(verbose=True)

                progress.update(task, completed=len(pending))

            # Show results
            if failed > 0:
                self.console.print(f"\n[red]✗ {failed} migration(s) failed[/red]")
                for error in errors:
                    self.console.print(f"[red]{error}[/red]")
            else:
                self.console.print(f"\n[green]✓ Successfully applied {successful} migration(s)[/green]")

            Prompt.ask("\nPress Enter to continue")

        except Exception as e:
            self.console.print(f"[red]Error applying migrations: {e}[/red]")
            Prompt.ask("\nPress Enter to continue")

    def create_migration_interactive(self):
        """Interactively create a new migration"""
        try:
            self.console.print("\n[bold]Create New Migration[/bold]")

            description = Prompt.ask("Description")
            file_type = Prompt.ask("Type", choices=["sql", "py"], default="sql")

            file_path = create_migration_file(description, file_type=file_type)

            self.console.print(f"\n[green]✓ Created: {file_path.name}[/green]")
            self.console.print(f"Path: {file_path}")

            Prompt.ask("\nPress Enter to continue")

        except Exception as e:
            self.console.print(f"[red]Error creating migration: {e}[/red]")
            Prompt.ask("\nPress Enter to continue")

    def generate_with_ai_interactive(self):
        """Interactively generate migration with AI"""
        try:
            # Check if AI is available
            generator = get_ai_generator()
            if not generator.is_available():
                self.console.print("\n[red]✗ AI generation not available[/red]")
                self.console.print("\nNo API keys configured")
                self.console.print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
                Prompt.ask("\nPress Enter to continue")
                return

            self.console.print("\n[bold cyan]✨ AI Migration Generator[/bold cyan]")
            self.console.print("=" * 50)

            prompt = Prompt.ask("\nDescribe your migration")
            file_type = Prompt.ask("Type", choices=["sql", "py"], default="sql")

            # Generate with progress
            self.console.print("\n[cyan]Generating with AI...[/cyan]")
            result = generate_migration_with_ai(
                prompt=prompt,
                file_type=file_type,
                include_context=True
            )

            # Display results
            self.console.print("\n" + "=" * 50)
            self.console.print(f"[bold]Description:[/bold] {result.description}")
            self.console.print(f"[bold]Confidence:[/bold] {result.confidence:.0%}")

            if result.warnings:
                self.console.print("\n[yellow]⚠ Warnings:[/yellow]")
                for warning in result.warnings:
                    self.console.print(f"  • {warning}")

            if result.suggestions:
                self.console.print("\n[cyan]💡 Suggestions:[/cyan]")
                for suggestion in result.suggestions:
                    self.console.print(f"  • {suggestion}")

            # Show generated SQL
            self.console.print("\n[bold]Generated SQL:[/bold]")
            self.console.print(Panel(result.sql, border_style="green"))

            if result.rollback_sql:
                self.console.print("\n[bold]Rollback SQL:[/bold]")
                self.console.print(Panel(result.rollback_sql, border_style="yellow"))

            # Save option
            if result.confidence > 0.0:
                if Confirm.ask("\nSave this migration?"):
                    file_path = create_migration_file(
                        description=result.description,
                        content=result.sql,
                        file_type=file_type
                    )
                    self.console.print(f"\n[green]✓ Saved: {file_path.name}[/green]")
                else:
                    self.console.print("\n[yellow]Migration not saved[/yellow]")
            else:
                self.console.print("\n[red]✗ Generation failed - not saving[/red]")

            Prompt.ask("\nPress Enter to continue")

        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            Prompt.ask("\nPress Enter to continue")

    def show_menu(self):
        """Display main menu"""
        menu = Table(show_header=False, box=None, padding=(0, 2))
        menu.add_column("Key", style="cyan bold")
        menu.add_column("Action")

        menu.add_row("1", "Status")
        menu.add_row("2", "List Migrations")
        menu.add_row("3", "Create Migration")
        menu.add_row("4", "Apply Pending")
        menu.add_row("5", "Compliance")
        menu.add_row("6", "Generate with AI ✨")
        menu.add_row("R", "Refresh")
        menu.add_row("Q", "Quit")

        self.console.print("\n")
        self.console.print(Panel(menu, title="[bold]Quick Actions[/bold]", border_style="cyan"))

    def run(self):
        """Main TUI loop"""
        try:
            while self.running:
                self.clear()
                self.show_header()
                self.show_status()
                self.show_menu()

                choice = Prompt.ask("\nCommand", default="1").lower()

                if choice == "1":
                    self.clear()
                    self.show_header()
                    self.show_status()
                    Prompt.ask("\nPress Enter to continue")

                elif choice == "2":
                    self.clear()
                    self.show_header()
                    self.show_migrations()
                    Prompt.ask("\nPress Enter to continue")

                elif choice == "3":
                    self.create_migration_interactive()

                elif choice == "4":
                    self.apply_migrations_interactive()

                elif choice == "5":
                    self.clear()
                    self.show_header()
                    self.show_compliance()
                    Prompt.ask("\nPress Enter to continue")

                elif choice == "6":
                    self.generate_with_ai_interactive()

                elif choice == "r":
                    continue  # Refresh

                elif choice == "q":
                    if Confirm.ask("Are you sure you want to quit?"):
                        self.running = False

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
        finally:
            self.console.print("\n[cyan]Goodbye![/cyan]")


def main():
    """Entry point for TUI"""
    tui = MigrationTUI()
    tui.run()


if __name__ == "__main__":
    main()
