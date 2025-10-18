# CI/CD Setup Guide

This document explains the CI/CD configuration and how to resolve billing issues.

## Current Status: Lite Mode

The repository is currently running **CI/CD Lite Mode** to conserve GitHub Actions minutes. This runs only essential checks:

- ✅ Code formatting (black, isort)
- ✅ Linting (flake8)
- ✅ Security scanning (bandit)
- ✅ Import verification
- ✅ Fast unit tests (no database)

## GitHub Actions Billing Issue

### Problem
GitHub Actions failed with this error:
> "The job was not started because recent account payments have failed or your spending limit needs to be increased"

### Solutions

#### Option 1: Increase Spending Limit (Recommended for Teams)
1. Go to [GitHub Billing Settings](https://github.com/settings/billing)
2. Navigate to "Spending limits" section
3. Increase the Actions spending limit
4. Verify payment method is valid

GitHub Free tier includes:
- **2,000 minutes/month** for private repositories
- **Unlimited minutes** for public repositories

#### Option 2: Make Repository Public
```bash
gh repo edit zeidalqadri/dbcooper --visibility public
```

Benefits:
- ✅ Unlimited GitHub Actions minutes
- ✅ Free CI/CD for open source
- ❌ Code is publicly visible

#### Option 3: Run Tests Locally (Current Setup)
The repository is configured for comprehensive local testing:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run full test suite
pytest tests/ -v --cov=src --cov-report=html

# Run all quality checks
black --check src tests
isort --check-only src tests
flake8 src tests --max-line-length=120
mypy src --ignore-missing-imports
bandit -r src
```

#### Option 4: Use Alternative CI/CD

**CircleCI Free Tier:**
- 6,000 build minutes/month
- Configuration: `.circleci/config.yml`

**Travis CI Free Tier:**
- 10,000 credits for open source
- Configuration: `.travis.yml`

**GitLab CI:**
- 400 minutes/month (free tier)
- Requires GitLab repository

## Enabling Full CI/CD

Once billing is resolved, enable the full CI/CD pipeline:

```bash
# Disable lite mode
mv .github/workflows/ci-lite.yml .github/workflows/ci-lite.yml.disabled

# Enable full mode
mv .github/workflows/ci-full.yml.disabled .github/workflows/ci.yml

# Commit and push
git add .github/workflows/
git commit -m "Enable full CI/CD pipeline"
git push
```

## Full CI/CD Features

When enabled, the full pipeline includes:

### Test Matrix
- ✅ Python 3.10, 3.11, 3.12
- ✅ PostgreSQL 16 service container
- ✅ Multiple OS support (Ubuntu)

### Quality Checks
- ✅ Code formatting (black, isort)
- ✅ Linting (flake8, pylint)
- ✅ Type checking (mypy)
- ✅ Security scanning (bandit, safety)

### Testing
- ✅ Unit tests with fixtures
- ✅ Integration tests with PostgreSQL
- ✅ Coverage reporting (target: 70%+)
- ✅ Upload coverage to Codecov

### Frontend Pipeline
- ✅ Node.js 20 setup
- ✅ npm install and build
- ✅ Frontend linting (if configured)
- ✅ Build artifact upload

### Deployment
- ✅ Docker build validation
- ✅ Deployment readiness checks
- ✅ Security report generation

## Cost Optimization

### Reduce CI Minutes Usage

1. **Run tests in parallel**
```yaml
strategy:
  matrix:
    python-version: ['3.11']  # Only one version
```

2. **Cache dependencies**
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
```

3. **Skip unnecessary jobs**
```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

4. **Use concurrency limits**
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Monitoring Usage

Check your Actions usage:
```bash
gh api /user/settings/billing/actions
```

View workflow runs:
```bash
gh run list --limit 10
```

## Local Pre-commit Checks

Install pre-commit hooks to catch issues before pushing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

This prevents pushing code that would fail CI/CD checks.

## Recommended Workflow

### For Personal/Small Projects (Current Setup)
1. ✅ Use CI/CD Lite Mode
2. ✅ Run full tests locally
3. ✅ Install pre-commit hooks
4. ✅ Test before pushing

### For Team/Production Projects
1. ✅ Enable full CI/CD pipeline
2. ✅ Configure branch protection rules
3. ✅ Require tests to pass before merge
4. ✅ Set up deployment automation

## Branch Protection Rules

Recommended settings for `main` branch:

```bash
# Enable via GitHub Settings > Branches > Add rule
```

- ✅ Require pull request reviews (1+ reviewer)
- ✅ Require status checks to pass
- ✅ Require branches to be up to date
- ✅ Require conversation resolution
- ✅ Require signed commits (optional)
- ❌ Allow force pushes
- ❌ Allow deletions

## Support

### GitHub Actions Documentation
- [Billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-github-actions)
- [Usage limits](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)
- [Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### Contact GitHub Support
- [GitHub Support](https://support.github.com/)
- [Community Forum](https://github.community/)

## Current Configuration Summary

```
📁 .github/workflows/
├── ci-lite.yml                    # ✅ ACTIVE: Lightweight checks
└── ci-full.yml.disabled           # ⏸️  DISABLED: Full pipeline
```

**When to use each:**
- **Lite**: Testing on GitHub Free tier with limited minutes
- **Full**: Production-ready pipeline with comprehensive checks

---

**Status**: Running in Lite Mode
**Action Required**: Update billing settings or run tests locally
**Impact**: Essential checks run, full tests must be run locally
