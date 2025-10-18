# Testing Guide

This guide covers how to run tests locally and understand the test suite.

## Quick Start

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (fast, no external dependencies)
│   ├── test_migration_executor.py
│   └── test_compliance_checker.py
└── integration/             # Integration tests (slower, may need DB/API)
    └── test_api.py
```

## Running Specific Tests

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run a specific test file
pytest tests/unit/test_migration_executor.py -v

# Run a specific test function
pytest tests/unit/test_migration_executor.py::test_initialization -v

# Run tests matching a pattern
pytest tests/ -k "migration" -v
```

## Test Markers

Tests are marked with categories for selective execution:

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Run tests that require database
pytest tests/ -m requires_db

# Skip slow tests
pytest tests/ -m "not slow"
```

## Environment Setup

Tests use environment variables for configuration:

```bash
# For in-memory testing (default)
export DATABASE_URL="sqlite:///:memory:"
export TESTING=true

# For PostgreSQL testing
export DATABASE_URL="postgresql://test_user:test_pass@localhost:5432/test_db"

# Disable features during testing
export ENFORCE_COMPLIANCE=false
export ENABLE_AI_GENERATION=false
```

## Coverage Requirements

- Target: 70%+ coverage
- Critical paths must be covered
- New code should include tests

```bash
# Check coverage
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report
pytest tests/ --cov=src --cov-report=html

# Fail if coverage is below threshold
pytest tests/ --cov=src --cov-fail-under=70
```

## Code Quality Checks

### Formatting
```bash
# Check code formatting
black --check src tests

# Auto-format code
black src tests

# Check import sorting
isort --check-only src tests

# Auto-sort imports
isort src tests
```

### Linting
```bash
# Run flake8
flake8 src tests --max-line-length=120

# Run pylint
pylint src

# Type checking
mypy src --ignore-missing-imports
```

### Security Scanning
```bash
# Run bandit security scanner
bandit -r src

# Check for vulnerable dependencies
safety check
```

## Pre-commit Hooks

Install pre-commit hooks to run checks automatically:

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

## CI/CD vs Local Testing

### Local Testing (Recommended)
- **Faster**: No queue time, runs immediately
- **Full control**: Run specific tests, debug easily
- **No cost**: No GitHub Actions minutes used
- **Better feedback**: See detailed output in real-time

### CI/CD Testing
- **Automated**: Runs on every push/PR
- **Multiple environments**: Tests Python 3.10, 3.11, 3.12
- **Integration**: Tests with real PostgreSQL
- **Quality gates**: Prevents merging broken code

**Current Status**: CI/CD is in "lite mode" to conserve GitHub Actions minutes. Run full tests locally before pushing.

## Test Writing Guidelines

### Unit Test Example
```python
def test_migration_executor_initialization():
    """Test that MigrationExecutor initializes correctly."""
    with patch('src.migration_executor.get_engine') as mock_engine:
        executor = MigrationExecutor(dry_run=True, verbose=False)
        assert executor.dry_run is True
        assert executor.verbose is False
        mock_engine.assert_called_once()
```

### Integration Test Example
```python
@pytest.mark.integration
def test_api_health_endpoint(test_client):
    """Test health endpoint returns correct status."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Fixture Example
```python
@pytest.fixture
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    # Setup
    yield engine
    # Teardown
    engine.dispose()
```

## Troubleshooting

### Import Errors
```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

### Database Connection Errors
```bash
# Use in-memory SQLite for tests
export DATABASE_URL="sqlite:///:memory:"

# Check PostgreSQL is running
pg_isready -h localhost -p 5432
```

### Test Failures
```bash
# Show full traceback
pytest tests/ -v --tb=long

# Stop at first failure
pytest tests/ -x

# Show print statements
pytest tests/ -v -s

# Re-run only failed tests
pytest tests/ --lf
```

### Coverage Issues
```bash
# Show which lines aren't covered
pytest tests/ --cov=src --cov-report=term-missing

# Generate HTML report for detailed view
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Performance

### Fast Test Runs
```bash
# Run in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Run only fast tests
pytest tests/ -m "not slow"

# Exit on first failure
pytest tests/ -x
```

### Test Selection
```bash
# Run tests modified recently
pytest tests/ --lf

# Run failed tests first
pytest tests/ --ff
```

## Continuous Testing

### Watch Mode
```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw tests/
```

### Git Hooks
Pre-commit hooks automatically run tests on commit:
- Formatting checks (black, isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [GitHub Actions Billing](https://github.com/settings/billing)

## Need Help?

- Check test output for error messages
- Review test fixtures in `tests/conftest.py`
- Look at existing tests for examples
- Run tests with `-v` for verbose output
- Use `--tb=long` for full tracebacks
