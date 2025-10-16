# AI-Powered Migration Generation Guide

Generate database migrations from natural language using AI! ✨

---

## 🚀 Quick Start

### Setup (One-time)

**Option 1: OpenAI (Recommended)**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Option 2: Anthropic Claude**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**Option 3: Both (Auto-fallback)**
```bash
export OPENAI_API_KEY="sk-your-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### Generate Your First Migration

**CLI:**
```bash
python -m src.cli generate "Add email column to users table"
```

**Terminal UI:**
```bash
python -m src.tui
# Press 6 for "Generate with AI ✨"
```

**API:**
```bash
curl -X POST http://localhost:8000/api/migrations/generate-ai \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add email to users", "save_immediately": true}'
```

---

## 💡 How It Works

### The AI Process

1. **Understand Your Request**: AI analyzes your natural language description
2. **Fetch Database Context**: System reads your current schema (tables, columns, indexes)
3. **Generate SQL**: AI creates idempotent, best-practice SQL
4. **Add Safeguards**: Includes IF NOT EXISTS, indexes, rollback SQL
5. **Confidence Score**: Tells you how certain the AI is (0-100%)
6. **Warnings & Suggestions**: Points out potential issues and improvements

### What Makes It Smart

- **Schema-Aware**: Knows your existing tables and columns
- **Best Practices**: Always adds indexes, timestamps, proper constraints
- **Idempotent**: Uses IF NOT EXISTS/IF EXISTS patterns
- **Safe**: Generates rollback SQL automatically
- **PostgreSQL-Optimized**: Dialect-specific features

---

## 📝 Writing Effective Prompts

### Simple Prompts (Recommended)

```
✓ "Add email column to users table"
✓ "Create posts table with user relationship"
✓ "Add index on users.email"
✓ "Add timestamps to posts table"
```

### Medium Complexity

```
✓ "Create full-text search on articles title and body"
✓ "Add soft delete with deleted_at column to users"
✓ "Create many-to-many between users and roles"
```

### Advanced

```
✓ "Migrate from email auth to OAuth with provider and external_id, preserving data"
✓ "Add audit logging table tracking changes to users and posts"
✓ "Create partitioned table for logs by month with retention policy"
```

### Tips for Best Results

**DO:**
- Be specific about table and column names
- Mention relationships explicitly
- State your intent clearly
- Use database terminology

**DON'T:**
- Be vague ("make it better")
- Skip table names ("add a column")
- Use ambiguous references ("the main table")
- Request destructive changes without confirmation

---

## 🎯 Usage Examples

### CLI

#### Basic Generation
```bash
python -m src.cli generate "Add created_at timestamp to posts"
```

#### Interactive Mode
```bash
python -m src.cli generate
# Will prompt: "Describe your migration:"
```

#### With Auto-Apply
```bash
python -m src.cli generate --apply "Add email index"
# Generates, saves, and applies immediately
```

#### Skip Database Context
```bash
python -m src.cli generate --no-context "Create users table"
# Faster but less context-aware
```

#### Python Migration
```bash
python -m src.cli generate --py "Complex data transformation"
```

#### Verbose Output
```bash
python -m src.cli -v generate "Add column"
# Shows AI reasoning and detailed info
```

### Terminal UI

```bash
python -m src.tui

# Main Menu:
# ╔════════════════════════════════╗
# ║  [6] Generate with AI ✨       ║
# ╚════════════════════════════════╝

# Interactive flow:
# 1. Press "6"
# 2. Enter description
# 3. Choose SQL or Python
# 4. Review generated code
# 5. Save if satisfied
```

### API

#### Generate Only
```bash
POST /api/migrations/generate-ai
{
  "prompt": "Add email to users",
  "file_type": "sql",
  "include_context": true,
  "save_immediately": false
}
```

Response:
```json
{
  "sql": "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;...",
  "rollback_sql": "ALTER TABLE users DROP COLUMN IF EXISTS email;",
  "confidence": 0.95,
  "warnings": ["Existing rows will have NULL emails"],
  "suggestions": ["Add NOT NULL after backfilling data"],
  "description": "Add email column to users table",
  "reasoning": "Used UNIQUE to prevent duplicates...",
  "saved": false,
  "file_path": null
}
```

#### Generate and Save
```bash
POST /api/migrations/generate-ai
{
  "prompt": "Create posts table",
  "save_immediately": true
}
```

---

## 🔍 Understanding the Output

### Confidence Scores

| Score | Meaning | Recommendation |
|-------|---------|---------------|
| 90-100% | Very confident | Safe to use as-is |
| 75-89% | Confident | Review before applying |
| 50-74% | Moderate | Carefully review and test |
| 25-49% | Low | Likely needs editing |
| 0-24% | Very low | Manually write instead |

### Warnings

Yellow flags about potential issues:
- "Existing rows will have NULL values"
- "This may lock the table during execution"
- "Consider adding a default value"
- "Foreign key may fail if data doesn't exist"

### Suggestions

Blue recommendations for improvements:
- "Add NOT NULL constraint after backfilling"
- "Consider adding a composite index"
- "Add CASCADE DELETE for cleanup"
- "Use TIMESTAMPTZ for timezone awareness"

---

## 🛠️ Configuration

### Environment Variables

```bash
# AI Provider Selection
AI_PROVIDER=openai          # 'openai', 'claude', or 'auto' (default)

# OpenAI Configuration
OPENAI_API_KEY=sk-...       # Required for OpenAI
OPENAI_MODEL=gpt-4-turbo-preview  # Optional

# Claude Configuration
ANTHROPIC_API_KEY=sk-ant-...  # Required for Claude
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022  # Optional

# Database
DATABASE_URL=postgresql://...  # Required for schema context
```

### Provider Selection

The system automatically tries providers in order:
1. **Auto mode** (default): Tries OpenAI, then Claude
2. **Explicit**: Set `AI_PROVIDER=openai` or `AI_PROVIDER=claude`

Check available providers:
```bash
python -m src.cli generate
# Shows: "Available providers: OpenAI GPT-4, Anthropic Claude"
```

---

## 💰 Cost Estimates

### OpenAI GPT-4

- **Input**: $0.01 per 1K tokens
- **Output**: $0.03 per 1K tokens
- **Typical migration**: ~500 tokens = **$0.02**
- **100 migrations/month**: **~$2**

### Anthropic Claude

- Similar pricing to GPT-4
- Sometimes cheaper for larger contexts

### Cost Optimization

1. **Use `--no-context`** for simple migrations (no schema fetch)
2. **Batch generate** multiple related migrations
3. **Review and reuse** patterns for similar migrations
4. **Use cheaper models** for simple tasks (future feature)

---

## 🔒 Security & Privacy

### What Data Is Sent to AI?

**Always sent:**
- Your natural language prompt
- Target database type (PostgreSQL)

**Optionally sent** (with `include_context=true`):
- Table names
- Column names and types
- Index names
- Foreign key relationships

**Never sent:**
- Actual data from tables
- Connection strings
- Credentials
- Migration history

### Best Practices

1. **Review generated SQL** before applying to production
2. **Test in development** first
3. **Use descriptive prompts** (avoid sensitive info in prompts)
4. **Consider local models** for sensitive environments (future)
5. **Audit AI-generated migrations** like any other code

### Disable Context Sharing

```bash
# CLI
python -m src.cli generate --no-context "Create users table"

# API
{
  "prompt": "...",
  "include_context": false
}
```

---

## 🚨 Troubleshooting

### "AI generation not available"

**Problem**: No API keys configured

**Solution**:
```bash
export OPENAI_API_KEY=sk-your-key
# or
export ANTHROPIC_API_KEY=sk-ant-your-key
```

### "Rate limit exceeded"

**Problem**: Too many requests to AI API

**Solutions**:
- Wait a few minutes
- Use `--no-context` to reduce token usage
- Upgrade API plan

### "Generation failed with confidence 0%"

**Problem**: AI couldn't understand the request

**Solutions**:
- Be more specific in prompt
- Break complex changes into smaller migrations
- Try manual creation with `python -m src.cli create`

### "Checksum mismatch after generation"

**Problem**: File was modified after AI generation

**Solution**: This is expected - AI generates content, you review and may edit

### Low Confidence Scores

**Causes**:
- Ambiguous prompt
- Complex or unusual request
- Missing context

**Solutions**:
- Rephrase prompt more clearly
- Include more details
- Enable context with database schema

---

## 🎓 Example Workflows

### Workflow 1: Add New Column

```bash
# 1. Generate
python -m src.cli generate "Add phone_number to users"

# 2. Review output
#    ✓ Checks SQL syntax
#    ✓ Reads warnings
#    ✓ Reviews confidence score

# 3. Save when prompted
# 4. Apply
python -m src.cli apply
```

### Workflow 2: Create Related Tables

```bash
# Prompt: "Create posts table with title, body, user_id foreign key, and timestamps"

# Generated:
# CREATE TABLE IF NOT EXISTS posts (
#     id SERIAL PRIMARY KEY,
#     title VARCHAR(500) NOT NULL,
#     body TEXT NOT NULL,
#     user_id INTEGER NOT NULL,
#     created_at TIMESTAMP DEFAULT NOW(),
#     updated_at TIMESTAMP DEFAULT NOW(),
#     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
# );
# CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
# CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
```

### Workflow 3: Data Migration

```bash
# Prompt: "Add status column to orders with default 'pending'"

# AI generates:
# ALTER TABLE orders
# ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending' NOT NULL;
#
# CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
#
# Suggestions:
# - Consider ENUM type for status values
# - Add CHECK constraint for valid statuses
```

---

## 📊 Supported Operations

### ✅ Fully Supported

- **CREATE TABLE** - New tables with all constraints
- **ALTER TABLE ADD COLUMN** - New columns
- **CREATE INDEX** - Single and composite indexes
- **ALTER TABLE ADD CONSTRAINT** - Foreign keys, checks, unique
- **CREATE TYPE** - Enums and custom types
- **SIMPLE INSERTS** - Reference data

### ⚠️ Partially Supported

- **ALTER TABLE DROP** - Generated with warnings
- **COMPLEX DATA MIGRATIONS** - May need manual review
- **PYTHON MIGRATIONS** - Basic support
- **STORED PROCEDURES** - Simple ones only

### ❌ Not Recommended

- **DROP DATABASE/TABLE** - Too destructive for AI
- **GRANT/REVOKE** - Security-sensitive
- **VERY COMPLEX LOGIC** - Better written manually

---

## 🎯 Best Practices

### 1. Start Simple

Begin with straightforward migrations:
```bash
✓ "Add column X to table Y"
✓ "Create table Z with fields A, B, C"
```

### 2. Iterate

Generate, review, refine:
```bash
# First attempt
python -m src.cli generate "Add user roles"

# Review, then regenerate with more detail
python -m src.cli generate "Create roles table with name and permissions JSON column, add role_id to users"
```

### 3. Always Review

- **Read the generated SQL**
- **Check warnings and suggestions**
- **Test in development first**
- **Review rollback SQL**

### 4. Leverage Context

Enable context for better results:
```bash
✓ python -m src.cli generate "Add foreign key to posts"
  # AI sees existing tables and suggests correct relationship

✗ python -m src.cli generate --no-context "Add foreign key"
  # AI doesn't know what tables exist
```

### 5. Save Good Patterns

When AI generates something great, save the pattern:
```bash
# Create a templates/ directory
mkdir templates/

# Save good examples
cp migrations/20250116_add_timestamps.sql templates/add_timestamps_pattern.sql
```

---

##

 📚 FAQ

**Q: Is AI-generated SQL safe for production?**
A: Yes, if reviewed. Always review generated SQL before applying to production, just like manually-written migrations.

**Q: What if I don't have an API key?**
A: You can still use manual migration creation. AI generation is optional.

**Q: Does it work offline?**
A: No, requires API access. Local LLM support is planned for future release.

**Q: Can it handle complex data migrations?**
A: For simple transformations, yes. Complex logic is better written manually.

**Q: What about other databases (MySQL, SQLite)?**
A: Currently optimized for PostgreSQL. Other databases coming soon.

**Q: Is my database schema sent to AI?**
A: Only if `include_context=true` (default). Use `--no-context` to disable.

**Q: Can I use my own prompts/templates?**
A: Currently no, but custom system prompts are planned for v2.

**Q: What if generation fails?**
A: The system falls back to manual creation. You can always write migrations manually.

---

## 🔮 Future Features

- [ ] Local LLM support (no API required)
- [ ] Custom prompt templates
- [ ] Multi-step migration generation
- [ ] Migration suggestions from schema analysis
- [ ] Automatic test generation
- [ ] MySQL/SQLite optimization
- [ ] Voice input support
- [ ] IDE plugins

---

## 📖 Related Documentation

- [Main README](./README.md) - Overview and setup
- [UI Guide](./UI_GUIDE.md) - Web dashboard and TUI
- [Quick Start](./QUICK_START.md) - Get started in 5 minutes
- [API Docs](http://localhost:8000/docs) - REST API reference

---

## 💬 Getting Help

**AI generation not working?**
1. Check API key: `echo $OPENAI_API_KEY`
2. Test connection: `python -m src.cli generate "test"`
3. Check logs: `python -m src.cli -v generate "test"`

**Need migration help?**
- See example prompts above
- Check existing migrations: `python -m src.cli list`
- Ask in project issues/discussions

**Found a bug?**
- Report at GitHub issues
- Include: prompt, generated SQL, error message

---

**Happy generating! ✨**
