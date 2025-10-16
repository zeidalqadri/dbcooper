# Database Migration Management System

A comprehensive, enterprise-grade database migration management system with strict compliance enforcement and automated validation.

## Features

### Core Capabilities
- **Migration Pre-flight Verification** - Automatically validates migration state before schema modifications
- **Compliance Enforcement** - Blocks direct schema changes when pending migrations exist
- **Schema Modification Interception** - Database triggers and application-level middleware to prevent unauthorized DDL
- **Migration Execution Engine** - Safe, transaction-wrapped migration execution with automatic rollback
- **Checksum Validation** - Detects tampering by verifying migration file integrity
- **Comprehensive CLI** - Full-featured command-line interface for migration management
- **REST API** - FastAPI-based API for programmatic integration
- **Real-time Monitoring** - Track migration status, compliance state, and execution history

### Safety Features
- Transaction-wrapped execution with automatic rollback on failure
- Dry-run mode for testing migrations without execution
- Migration dependency tracking and ordering
- Failed migration detection and repair tools
- Orphaned migration detection
- Idempotency checks and enforcement

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL database (MySQL also supported)
- Node.js 18+ (for Web UI)
- Virtual environment (recommended)

### Setup

1. **Clone or navigate to the project directory**
```bash
cd db_migration_system
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure database connection**

Option 1: Environment variable
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

Option 2: Create `.db_uri` file
```bash
echo "postgresql://user:password@host:port/database" > .db_uri
```

5. **Initialize the database**
```bash
python -m src.cli init
```

This will:
- Create the `schema_migrations` tracking table
- Optionally install DDL triggers for schema interception
- Set up audit logging tables

6. **Set up Web UI (Optional)**
```bash
cd frontend
npm install
```

## CLI Usage

### Core Commands

#### Initialize Database
```bash
python -m src.cli init
```
Creates migration tracking tables and optionally installs DDL triggers.

#### Check Migration Status
```bash
python -m src.cli status
python -m src.cli status -v  # Verbose mode with more details
```
Shows current migration state, compliance status, pending migrations, and warnings.

#### Create New Migration
```bash
python -m src.cli create "create_users_table"
python -m src.cli create "add_email_column" --py  # Python migration
```
Generates a timestamped migration file in the `migrations/` directory.

#### Apply Pending Migrations
```bash
python -m src.cli apply
python -m src.cli apply --dry-run  # Test without executing
python -m src.cli apply -v  # Verbose output
```
Applies all pending migrations sequentially. Stops on first failure.

#### Rollback Migrations
```bash
python -m src.cli rollback 1  # Rollback last migration
python -m src.cli rollback 3  # Rollback last 3 migrations
python -m src.cli rollback 1 --dry-run  # Test rollback
```

#### Validate Compliance
```bash
python -m src.cli validate
```
Runs comprehensive compliance checks and reports violations.

#### View Migration History
```bash
python -m src.cli history
python -m src.cli history --limit 50  # Show last 50 migrations
```

#### List Available Migrations
```bash
python -m src.cli list
```
Shows all migration files and their application status.

#### Repair Failed Migrations
```bash
python -m src.cli repair
```
Removes failed migration records so you can retry them.

#### Test Database Connection
```bash
python -m src.cli connect-test
```

#### Manage Schema Interceptor
```bash
python -m src.cli interceptor --enable   # Enable DDL blocking
python -m src.cli interceptor --disable  # Disable DDL blocking
```

## REST API Usage

### Start the API Server

```bash
python -m src.api
```

Or with uvicorn directly:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Base URL**: http://localhost:8000/api

### API Endpoints

#### Health Check
```bash
GET /api/health
```

#### Migration Status
```bash
GET /api/migrations/status
```

#### List Applied Migrations
```bash
GET /api/migrations/applied?limit=100
```

#### List Pending Migrations
```bash
GET /api/migrations/pending
```

#### Apply Pending Migrations
```bash
POST /api/migrations/apply
Content-Type: application/json

{
  "dry_run": false,
  "verbose": true
}
```

#### Rollback Migrations
```bash
POST /api/migrations/rollback
Content-Type: application/json

{
  "count": 1,
  "dry_run": false
}
```

#### Create Migration
```bash
POST /api/migrations/create
Content-Type: application/json

{
  "description": "add_users_table",
  "file_type": "sql"
}
```

#### Get Compliance Report
```bash
GET /api/compliance/report
```

#### Validate Compliance
```bash
POST /api/compliance/validate
```
Returns HTTP 403 if violations detected, HTTP 200 if compliant.

#### Enforce Compliance
```bash
POST /api/compliance/enforce
```
Blocks with HTTP 403 if violations exist.

## Migration File Format

### SQL Migrations

Files must follow the naming convention: `YYYYMMDDHHMMSS_description.sql`

Example: `20250116120000_create_users_table.sql`

```sql
-- Migration: Create users table
-- Created: 2025-01-16T12:00:00

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

### Python Migrations

Files must follow the naming convention: `YYYYMMDDHHMMSS_description.py`

Example: `20250116120000_seed_initial_data.py`

```python
"""
Migration: Seed initial data
Created: 2025-01-16T12:00:00
"""

def up(connection):
    """Apply the migration."""
    from sqlalchemy import text

    connection.execute(text("""
        INSERT INTO users (username, email)
        VALUES ('admin', 'admin@example.com')
        ON CONFLICT (username) DO NOTHING
    """))

def down(connection):
    """Rollback the migration."""
    from sqlalchemy import text

    connection.execute(text("""
        DELETE FROM users WHERE username = 'admin'
    """))
```

## Compliance System

### Migration-First Principle

The system enforces a **migration-first principle**:

1. All schema changes MUST originate from migration files
2. Direct DDL statements are blocked when pending migrations exist
3. Migration checksums are validated to detect tampering
4. Failed migrations must be fixed before new ones can be applied

### Compliance Violations

The system detects and blocks the following violations:

#### Critical Violations (Block Operations)
- **Pending Migrations**: Unapplied migration files exist
- **Failed Migrations**: Previous migrations failed execution
- **Missing Schema Table**: Migration tracking table doesn't exist

#### High Severity Violations
- **Checksum Mismatches**: Migration files modified after application
- **Schema Drift**: Database schema doesn't match migration state

#### Medium Severity Violations
- **Orphaned Migrations**: Database records without corresponding files

### Compliance Workflow

```
┌─────────────────────────────────────────────────────┐
│  Attempt Schema Modification (CREATE/ALTER/DROP)    │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Pre-flight Verification                            │
│  1. Check migration table exists                    │
│  2. Query all applied migrations                    │
│  3. Scan migration files directory                  │
│  4. Compare applied vs available                    │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Compliance Enforcement                             │
│  - Pending migrations? → BLOCK                      │
│  - Failed migrations? → BLOCK                       │
│  - Checksum mismatch? → WARN + BLOCK                │
│  - In migration context? → ALLOW                    │
└─────────────────┬───────────────────────────────────┘
                  │
           ┌──────┴──────┐
           │             │
      COMPLIANT      VIOLATION
           │             │
           ▼             ▼
    ALLOW DDL    BLOCK + ERROR
```

## Schema Interception

### Two-Layer Protection

#### Layer 1: Database Triggers (PostgreSQL)
- Event triggers on DDL commands
- Logs all schema modifications to `ddl_audit_log` table
- Cannot fully block operations (PostgreSQL limitation)
- Provides audit trail

#### Layer 2: Application Middleware (SQLAlchemy)
- Intercepts DDL at application level
- **True blocking capability**
- Enforces compliance before execution
- Bypasses checks during migration execution

### Enable/Disable Interception

```python
from src.schema_interceptor import enable_schema_interception, disable_schema_interception

# Enable strict enforcement
enable_schema_interception(strict_mode=True)

# Disable (for emergencies only)
disable_schema_interception()
```

Or via CLI:
```bash
python -m src.cli interceptor --enable
python -m src.cli interceptor --disable
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Database Migration Check

on: [push, pull_request]

jobs:
  migration-compliance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Check migration compliance
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          python -m src.cli validate

      - name: Validate migration files
        run: |
          python -m src.cli list
```

### Pre-deployment Check

```bash
#!/bin/bash
# deploy.sh

echo "Running migration compliance check..."

python -m src.cli validate

if [ $? -ne 0 ]; then
  echo "❌ Deployment blocked: Migration compliance violations detected"
  exit 1
fi

echo "✅ Compliance check passed"

python -m src.cli apply

if [ $? -ne 0 ]; then
  echo "❌ Migration application failed"
  exit 1
fi

echo "✅ Migrations applied successfully"
echo "Proceeding with deployment..."
```

## Architecture

### Component Overview

```
┌────────────────────────────────────────────────────────────┐
│                     CLI / REST API                         │
├────────────────────────────────────────────────────────────┤
│  Migration Loader  │  Migration Executor  │  Compliance   │
│  - File scanning   │  - SQL execution     │  - Validation │
│  - Checksum calc   │  - Transaction mgmt  │  - Enforcement│
│  - Version parse   │  - Rollback logic    │  - Reporting  │
├────────────────────────────────────────────────────────────┤
│                 Schema Interceptor Layer                   │
│  - DDL detection   │  - Compliance checks │  - Bypass mgmt│
├────────────────────────────────────────────────────────────┤
│              Migration State Management                    │
│  - Applied migrations tracking                             │
│  - Pending migrations detection                            │
│  - Checksum verification                                   │
├────────────────────────────────────────────────────────────┤
│                      Database Layer                        │
│  - schema_migrations table                                 │
│  - ddl_audit_log table                                     │
│  - migration_execution_context table                       │
│  - DDL event triggers (PostgreSQL)                         │
└────────────────────────────────────────────────────────────┘
```

### File Structure

```
db_migration_system/
├── src/
│   ├── __init__.py
│   ├── cli.py                    # CLI commands
│   ├── api.py                    # FastAPI REST API
│   ├── config.py                 # Configuration management
│   ├── database.py               # Database connection
│   ├── migration_manager.py      # Schema migrations table
│   ├── migration_loader.py       # File scanning & parsing
│   ├── migration_executor.py     # Migration execution
│   ├── migration_state.py        # State tracking & queries
│   ├── compliance_checker.py     # Compliance validation
│   └── schema_interceptor.py     # DDL interception
├── migrations/
│   └── 00000000000000_setup_ddl_triggers.sql
├── requirements.txt
└── README.md
```

## Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Test connection
python -m src.cli connect-test

# Check your DATABASE_URL or .db_uri file
cat .db_uri
```

#### Pending Migrations Blocking Operations
```bash
# Check status
python -m src.cli status

# Apply pending migrations
python -m src.cli apply
```

#### Failed Migration
```bash
# View history to see error
python -m src.cli history

# Repair (remove failed record)
python -m src.cli repair

# Fix the migration file and retry
python -m src.cli apply
```

#### Checksum Mismatch
```bash
# View detailed status
python -m src.cli status -v

# This indicates a migration file was modified after being applied
# DO NOT modify applied migrations - create a new migration instead
python -m src.cli create "fix_previous_migration"
```

## Best Practices

### Migration Authoring

1. **Use descriptive names**: `create_users_table` not `migration1`
2. **Make migrations idempotent**: Use `IF NOT EXISTS` and `IF EXISTS`
3. **One logical change per migration**: Don't combine unrelated changes
4. **Test migrations locally first**: Use `--dry-run` mode
5. **Never modify applied migrations**: Create new migrations to fix issues
6. **Include rollback logic**: Add DROP statements or down() functions
7. **Add comments**: Document the purpose and reasoning

### Deployment Workflow

1. **Create migration** on development
2. **Test locally** with `--dry-run`
3. **Apply to dev database**
4. **Commit migration file** to version control
5. **Run compliance check** in CI
6. **Apply to staging**
7. **Validate in staging**
8. **Apply to production**

### Security Considerations

- Never commit `.db_uri` file to version control
- Use environment variables for production
- Restrict database user permissions
- Enable schema interceptor in production
- Review DDL audit logs regularly
- Use separate credentials for CI/CD

## User Interfaces

The system provides **two powerful interfaces**:

### 🌐 Web Dashboard (Recommended)

Modern, browser-based interface with real-time updates.

**Start the Web UI:**
```bash
# Terminal 1: Start API server
python -m src.api

# Terminal 2: Start frontend dev server
cd frontend
npm run dev
```

Access at: **http://localhost:3000**

**Features:**
- Real-time status updates via WebSocket
- Interactive dashboard with metrics
- SQL editor with syntax highlighting
- Migration history with analytics
- Compliance monitoring
- Mobile responsive
- Dark mode support

**Production Build:**
```bash
cd frontend
npm run build
# Serves from backend on port 8000
```

### 💻 Terminal UI (TUI)

Rich terminal interface for CLI enthusiasts and SSH access.

**Start the TUI:**
```bash
python -m src.tui
```

**Features:**
- Interactive menu system
- Color-coded output
- Live status updates
- Progress indicators
- Works over SSH
- Low resource usage

**Navigation:**
- `1-5`: Select menu option
- `R`: Refresh
- `Q`: Quit

See [UI_GUIDE.md](./UI_GUIDE.md) for comprehensive UI documentation.

## API Documentation

The REST API provides programmatic access to all features.

**Interactive API Docs:** http://localhost:8000/docs

**Key Endpoints:**
- `GET /api/migrations/status` - Get migration status
- `POST /api/migrations/apply` - Apply pending migrations
- `GET /api/compliance/report` - Get compliance report
- `WS /ws` - WebSocket for real-time updates

See the [API Documentation](http://localhost:8000/docs) for full endpoint reference.

## Support & Contributing

For issues, questions, or contributions, please refer to the project repository.

## License

[Your License Here]
