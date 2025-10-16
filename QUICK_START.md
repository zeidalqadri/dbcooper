# 🚀 Quick Start Guide

Get up and running with the DB Migration Manager in under 5 minutes.

---

## Prerequisites

- Python 3.12+
- Node.js 18+ (for Web UI only)
- PostgreSQL database

---

## Option 1: Web Dashboard (Recommended)

### Step 1: Install Backend Dependencies

```bash
# Clone/navigate to project
cd db_migration_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Configure Database

```bash
# Set database URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Or create .db_uri file
echo "postgresql://user:pass@host:port/dbname" > .db_uri
```

### Step 3: Initialize Database

```bash
python -m src.cli init
# Answer 'y' to install DDL triggers
```

### Step 4: Start Backend API

```bash
python -m src.api
# API running on http://localhost:8000
```

### Step 5: Start Frontend (New Terminal)

```bash
cd frontend
npm install
npm run dev
# UI running on http://localhost:3000
```

### Step 6: Open Browser

Visit **http://localhost:3000**

You should see:
- ✓ Live status dashboard
- Migration metrics
- Quick action buttons
- Recent migration history

🎉 **You're all set!**

---

## Option 2: Terminal UI (For CLI Users)

### Step 1-3: Same as Above

Follow steps 1-3 from Option 1 to install and initialize.

### Step 4: Launch TUI

```bash
python -m src.tui
```

You'll see an interactive menu:

```
╔════════════════════════════════╗
║  DB MIGRATION MANAGER v1.0.0   ║
╠════════════════════════════════╣
║  [1] Status                    ║
║  [2] List Migrations           ║
║  [3] Create Migration          ║
║  [4] Apply Pending             ║
║  [5] Compliance                ║
║  [R] Refresh    [Q] Quit       ║
╚════════════════════════════════╝
```

Press `1` to view status!

---

## Option 3: CLI Only (Minimal)

### Step 1-3: Same as Above

Follow steps 1-3 to install and initialize.

### Step 4: Use CLI Commands

```bash
# Check status
python -m src.cli status

# List migrations
python -m src.cli list

# Create migration
python -m src.cli create "add_users_table"

# Apply migrations
python -m src.cli apply

# View history
python -m src.cli history
```

---

## Next Steps

### Create Your First Migration

**Via Web UI:**
1. Click "Create New Migration"
2. Enter description
3. Edit SQL in the editor
4. Click "Save"

**Via TUI:**
1. Press `3`
2. Enter description
3. Choose SQL or Python
4. Edit the generated file

**Via CLI:**
```bash
python -m src.cli create "my_first_migration"
# Edit: migrations/YYYYMMDDHHMMSS_my_first_migration.sql
```

### Apply Your Migration

**Via Web UI:**
- Click "Apply Pending Migrations"

**Via TUI:**
- Press `4` → Confirm with `y`

**Via CLI:**
```bash
python -m src.cli apply
```

### Check Compliance

**Via Web UI:**
- Navigate to "Compliance" tab

**Via TUI:**
- Press `5`

**Via CLI:**
```bash
python -m src.cli validate
```

---

## Troubleshooting

### "Connection refused" on Web UI

**Problem**: Frontend can't connect to API

**Solution**:
```bash
# Ensure API is running in another terminal
python -m src.api
# Should see: "Database connection established"
```

### "Module not found"

**Problem**: Missing Python dependencies

**Solution**:
```bash
# Activate venv first!
source venv/bin/activate
pip install -r requirements.txt
```

### "Port 3000 already in use"

**Problem**: Another app using port 3000

**Solution**:
```bash
# Kill the process or change port
cd frontend
# Edit vite.config.ts, change port to 3001
npm run dev
```

### Database connection failed

**Problem**: Can't connect to database

**Solution**:
```bash
# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Test connection directly
python -m src.cli connect-test
```

---

## Common Workflows

### Workflow 1: Check System Health

```bash
# CLI
python -m src.cli status

# TUI
python -m src.tui  # Press 1

# Web
Open http://localhost:3000
```

### Workflow 2: Create and Apply Migration

```bash
# 1. Create
python -m src.cli create "add_email_to_users"

# 2. Edit the file
vim migrations/YYYYMMDDHHMMSS_add_email_to_users.sql

# 3. Apply
python -m src.cli apply

# 4. Verify
python -m src.cli history
```

### Workflow 3: Fix Failed Migration

```bash
# 1. Check what failed
python -m src.cli history

# 2. Remove failed record
python -m src.cli repair

# 3. Fix the migration file
vim migrations/YYYYMMDDHHMMSS_failed_migration.sql

# 4. Retry
python -m src.cli apply
```

---

## Example Migration

Create `migrations/20250116120000_create_users.sql`:

```sql
-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

Apply it:
```bash
python -m src.cli apply
```

---

## API Testing

### Via Browser

Visit: http://localhost:8000/docs

Interactive Swagger UI with all endpoints.

### Via curl

```bash
# Get status
curl http://localhost:8000/api/migrations/status

# Apply migrations
curl -X POST http://localhost:8000/api/migrations/apply \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### Via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  console.log('Status update:', JSON.parse(event.data));
};
```

---

## Environment Variables

Create `.env` in project root:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# API (optional)
API_HOST=0.0.0.0
API_PORT=8000

# Frontend (optional)
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

Load with:
```bash
source .env  # or
export $(cat .env | xargs)
```

---

## Production Deployment

### Option 1: Single Container

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Run combined server (coming soon)
python -m src.ui_server
```

### Option 2: Separate Services

```bash
# Terminal 1: API
python -m src.api --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (nginx)
cd frontend/dist
python -m http.server 3000
```

### Option 3: Docker

```bash
# Coming soon
docker-compose up
```

---

## Getting Help

- **Documentation**: See [README.md](./README.md)
- **UI Guide**: See [UI_GUIDE.md](./UI_GUIDE.md)
- **API Docs**: http://localhost:8000/docs
- **Issues**: [GitHub Issues]

---

## Keyboard Shortcuts

### Web UI
- `/` - Search
- `n` - New migration
- `a` - Apply pending
- `r` - Refresh
- `?` - Help

### TUI
- `1-5` - Menu options
- `R` - Refresh
- `Q` - Quit
- `Enter` - Confirm
- `Esc` - Cancel

### CLI
- `Ctrl+C` - Cancel operation
- `Tab` - Auto-complete (if enabled)

---

## Tips & Tricks

1. **Keep TUI open**: Run in tmux/screen for persistent session
2. **Watch mode**: Use `watch python -m src.cli status`
3. **JSON output**: Pipe CLI to `jq` for parsing
4. **Log everything**: Redirect to file with `| tee migration.log`
5. **Quick status**: Add alias: `alias mig-status='python -m src.cli status'`

---

## What's Next?

✅ **You're ready to go!**

- Create your first migration
- Explore the Web UI features
- Try the Terminal UI
- Read the full documentation

**Happy migrating! 🎉**
