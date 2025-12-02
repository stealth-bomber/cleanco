# Testing Guide for cleanco

## Quick Start

The easiest way to run tests is using pytest directly:

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_cleanname.py

# Run a specific test function
pytest tests/test_cleanname.py::test_finnish_branch_patterns
```

## Environment Setup

### Option 1: Using pip (Recommended)

1. **Install dependencies:**
   ```bash
   pip install pytest pytest-runner
   ```

2. **Run tests:**
   ```bash
   pytest tests/
   ```

### Option 2: Using setup.py (as mentioned in README)

1. **Install the package in development mode:**
   ```bash
   pip install -e .
   ```
   This installs the package and its test dependencies (pytest, tox).

2. **Run tests:**
   ```bash
   python setup.py test
   ```

### Option 3: Using tox (for multiple Python versions)

If you want to test against multiple Python versions (as configured in `tox.ini`):

1. **Install tox:**
   ```bash
   pip install tox
   ```

2. **Run tests:**
   ```bash
   tox
   ```

   This will run tests against Python 3.6, 3.7, 3.8, and 3.9 (as configured in tox.ini).

## Python Version Requirements

- The project supports Python 3.6+ (as per tox.ini configuration)
- Your current Python version: 3.14.0 (should work fine)

## Running Specific Tests

### Run only Finnish branch pattern tests:
```bash
pytest tests/test_cleanname.py::test_finnish_branch_patterns -v
```

### Run with output capture disabled (see print statements):
```bash
pytest tests/ -v -s
```

### Run tests and show coverage:
```bash
pip install pytest-cov
pytest tests/ --cov=cleanco --cov-report=html
```

## Troubleshooting

### Issue: "No module named pytest"
**Solution:** Install pytest:
```bash
pip install pytest
```

### Issue: "No module named setuptools"
**Solution:** Install setuptools:
```bash
pip install setuptools
```

### Issue: Tests pass but you want to verify manually
You can also test interactively in Python:
```python
from cleanco import basename

# Test a specific case
result = basename("Nordisk Kellogg Finland, Nordisk Kellogg ApS, filial i Finland",
                  prefix=True, suffix=True, middle=True)
print(result)  # Should print: "Nordisk Kellogg"
```

## Test Structure

- All tests are in the `tests/` directory
- Main test file: `tests/test_cleanname.py`
- Tests use pytest's parametrize decorator for multiple test cases
- Tests are organized by functionality (basic cleanups, Finnish branch patterns, etc.)

