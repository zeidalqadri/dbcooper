#!/bin/bash
# Script to push branches and create pull request

set -e  # Exit on error

echo "🚀 Pushing branches to GitHub..."

# Push main branch (base branch with initial system)
echo "📤 Pushing main branch..."
git push -u origin main

# Push security-hardening branch (with security improvements)
echo "📤 Pushing security-hardening branch..."
git push -u origin security-hardening

# Set main as default branch on GitHub
echo "⚙️  Setting main as default branch..."
gh repo edit zeidalqadri/dbcooper --default-branch main

# Create pull request
echo "📝 Creating pull request..."
gh pr create --base main --head security-hardening \
  --title "Add critical security hardening and comprehensive test suite" \
  --body "## 🔒 Security Hardening & Testing Infrastructure

This PR addresses all critical security issues and implements a comprehensive test suite for production readiness.

### Security Improvements
- ✅ Add \`.gitignore\` to prevent credential leaks (.db_uri, .env, API keys)
- ✅ Create \`.env.example\` template with all required environment variables
- ✅ Fix credential handling: remove interactive input, fail fast on missing config
- ✅ Add \`SECURITY.md\` with best practices and vulnerability reporting process
- ✅ Configure pre-commit hooks for security scanning (bandit, detect-private-key)
- ✅ Pin all dependency versions to prevent supply chain attacks
- ✅ Add centralized configuration management

### Test Suite
- ✅ Comprehensive pytest configuration with 70%+ coverage target
- ✅ 52+ test cases covering critical paths:
  - 17 unit tests for migration_executor
  - 20+ unit tests for compliance_checker
  - 15+ integration tests for API endpoints
- ✅ Mock implementations for all external dependencies
- ✅ Database fixtures with SQLite in-memory
- ✅ AI provider mocking (OpenAI/Claude)

### CI/CD Pipeline
- ✅ GitHub Actions workflow with Python 3.10, 3.11, 3.12
- ✅ PostgreSQL service container for integration tests
- ✅ Automated linting, type checking, security scanning
- ✅ Test coverage reporting to Codecov
- ✅ Frontend build and test pipeline
- ✅ Artifact upload for test results and security reports

### Development Tools
- ✅ requirements-dev.txt with testing and quality tools
- ✅ black, isort, flake8 for code formatting
- ✅ mypy for type checking
- ✅ bandit for security scanning
- ✅ pre-commit hooks for automated checks
- ✅ pyproject.toml for tool configuration

### Files Changed
\`\`\`
17 files changed, 2,375 insertions(+), 26 deletions(-)
\`\`\`

### Impact
- **Prevents credential exposure** through proper .gitignore
- **Establishes testing foundation** for production deployment
- **Automates quality checks** via CI/CD pipeline
- **Ensures code security** before production use

### Testing
\`\`\`bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run security scan
bandit -r src

# Install pre-commit hooks
pre-commit install
\`\`\`

### Next Steps After Merge
1. Set up environment variables (use .env.example as template)
2. Run tests locally to verify setup
3. Configure GitHub branch protection rules
4. Add authentication middleware for production
5. Enable rate limiting on API endpoints
6. Set up monitoring and alerting

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)"

echo ""
echo "✅ Done! Pull request created successfully."
echo "🔗 View at: https://github.com/zeidalqadri/dbcooper/pulls"
