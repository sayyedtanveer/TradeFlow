# Test Suite Quick Start Guide

## Installation & Setup

### 1. Install Test Dependencies (Already in requirements.txt)
```bash
cd backend
pip install pytest pytest-asyncio pytest-cov
```

### 2. Run All Tests
```bash
pytest tests/ -v
```

### 3. Check Coverage
```bash
pytest tests/ --cov=backend/app --cov-report=term-missing
```

---

## Common Tasks

### Run tests for a specific module
```bash
# BOM tests
pytest tests/unit/bom/ tests/api/bom/ tests/e2e/ -v

# Product tests
pytest tests/unit/product/ tests/api/product/ -v

# Operations tests
pytest tests/unit/operations/ tests/api/operations/ -v

# Inventory tests
pytest tests/unit/inventory/ -v
```

### Run just unit tests
```bash
pytest tests/unit/ -v
```

### Run just API tests
```bash
pytest tests/api/ -v
```

### Run just E2E tests
```bash
pytest tests/e2e/ -v
```

### Run a single test file
```bash
pytest tests/unit/bom/test_bom_domain.py -v
```

### Run a single test class
```bash
pytest tests/unit/bom/test_bom_domain.py::TestBOMCreation -v
```

### Run a single test method
```bash
pytest tests/api/bom/test_bom_api.py::TestBOMAPI::test_create_bom_success -v
```

### Run tests with coverage report
```bash
# Terminal report
pytest tests/ --cov=backend/app --cov-report=term-missing

# HTML report (open htmlcov/index.html in browser)
pytest tests/ --cov=backend/app --cov-report=html
```

---

## Writing New Tests

### Create a Unit Test

1. **Create test file** in appropriate module:
   ```bash
   backend/tests/unit/bom/test_bom_new_feature.py
   ```

2. **Write test class and methods**:
   ```python
   from backend.tests.conftest_factories import create_bom_payload
   
   
   class TestNewBOMFeature:
       """Test new BOM feature."""
       
       def test_new_feature_success(self):
           """Test new feature works correctly."""
           payload = create_bom_payload()
           # Add your test logic
           assert payload["version"] == "v1.0"
   ```

3. **Run your test**:
   ```bash
   pytest backend/tests/unit/bom/test_bom_new_feature.py -v
   ```

### Create an API Test

1. **Create test file**:
   ```bash
   backend/tests/api/bom/test_new_endpoint.py
   ```

2. **Write test using async client**:
   ```python
   import pytest
   from httpx import AsyncClient
   
   
   @pytest.mark.asyncio
   class TestNewEndpoint:
       """Test new API endpoint."""
       
       async def test_endpoint_success(self, authenticated_async_client: AsyncClient):
           """Test endpoint returns 200."""
           response = await authenticated_async_client.get("/api/v1/new-endpoint")
           assert response.status_code == 200
   ```

3. **Run your test**:
   ```bash
   pytest backend/tests/api/bom/test_new_endpoint.py -v
   ```

### Create an E2E Test

1. **Add to** `backend/tests/e2e/test_full_bom_flow.py`:

2. **Write test using fixtures**:
   ```python
   @pytest.mark.asyncio
   async def test_new_workflow_scenario(
       self, 
       authenticated_async_client: AsyncClient,
       e2e_test_context: dict,
   ):
       """Test new workflow."""
       # Use e2e_test_context to track created IDs
       # Use authenticated_async_client to make API calls
       pass
   ```

---

## Using Factories for Test Data

### Create Test Data with Factories

```python
from backend.tests.conftest_factories import (
    create_product_template_payload,
    create_bom_payload,
    create_material_payload,
    generate_uuid,
)


def test_with_factories():
    # Create product template
    product = create_product_template_payload(
        name="Custom Product",
        code="CUSTOM-001"
    )
    
    # Create BOM with custom product
    bom = create_bom_payload(
        product_id=product["id"],
        version="v2.0"
    )
    
    # Create material
    material = create_material_payload(
        code="MAT-CUSTOM",
        unit_cost=150.00
    )
    
    # Generate test IDs
    test_id = generate_uuid()
```

### Available Factories

- `create_product_template_payload()`
- `create_product_variant_payload()`
- `create_bom_payload()`
- `create_bom_line_payload()`
- `create_bom_with_lines_payload()`
- `create_material_payload()`
- `create_operation_payload()`
- `create_stock_adjustment_payload()`
- `create_batch_payload()`
- `create_workstation_payload()`
- `generate_uuid()`
- `generate_test_id(prefix)`

See `backend/tests/conftest_factories.py` for full documentation.

---

## Using Fixtures

### Available Core Fixtures

```python
# Use in your test
@pytest.mark.asyncio
async def test_api_call(authenticated_async_client: AsyncClient):
    """Access authenticated client."""
    response = await authenticated_async_client.get("/api/v1/boms")
    assert response.status_code == 200


def test_with_database(db_session):
    """Access test database."""
    # Query database
    pass


def test_with_context(test_tenant_id, test_user_id):
    """Access test tenant and user IDs."""
    assert test_tenant_id is not None
```

### Available Fixtures

- `async_client` - Async HTTP client (auto-injected DB)
- `authenticated_async_client` - Async client with auth headers
- `sync_client` - Sync HTTP client
- `authenticated_sync_client` - Sync client with auth headers
- `db_session` - Test database session
- `token_headers` - Authorization headers with JWT
- `test_tenant_id` - Test tenant UUID
- `test_user_id` - Test user UUID
- `test_user_email` - Test user email
- `test_user_password` - Test user password
- `sample_product_template` - Sample product with attributes
- `sample_bom_create_payload` - Sample BOM creation payload

---

## Test Best Practices

### ✅ DO

- ✅ Use factories to create test data (not hardcoded values)
- ✅ Keep tests focused (one behavior per test)
- ✅ Use descriptive test names (`test_create_bom_with_invalid_quantity_rejected`)
- ✅ Test both success and failure cases
- ✅ Handle 404 and 422 status codes in API tests
- ✅ Use fixtures for reusable data
- ✅ Mark async tests with `@pytest.mark.asyncio`
- ✅ Use parametrized tests for multiple scenarios

### ❌ DON'T

- ❌ Don't hardcode test data (use factories)
- ❌ Don't create interdependent tests
- ❌ Don't test implementation details
- ❌ Don't mock unnecessarily (use real DB)
- ❌ Don't ignore error cases
- ❌ Don't have tests that are too long
- ❌ Don't assume test execution order

---

## Troubleshooting

### Issue: Tests hang or timeout
**Solution**: Check for async/await issues. Make sure functions are awaited:
```python
# WRONG
response = authenticated_async_client.post(...)

# RIGHT
response = await authenticated_async_client.post(...)
```

### Issue: "fixture 'async_client' not found"
**Solution**: Ensure `backend/tests/conftest.py` exists and is in the tests directory.

### Issue: Database connection errors
**Solution**: Tests use in-memory SQLite. Make sure pytest is run from the project root:
```bash
cd /path/to/MedTrack
pytest backend/tests/ -v
```

### Issue: Import errors
**Solution**: Ensure `__init__.py` files exist in all test directories:
```bash
backend/tests/__init__.py
backend/tests/unit/__init__.py
backend/tests/unit/bom/__init__.py
# ... etc
```

---

## Performance Tips

### Run only affected tests
```bash
# Run BOM tests only
pytest tests/unit/bom/ tests/api/bom/ -v

# Run BOM unit tests (faster)
pytest tests/unit/bom/ -v
```

### Disable coverage for faster runs
```bash
# Without coverage
pytest tests/ -v

# With coverage (slower)
pytest tests/ --cov=backend/app --cov-report=term-missing
```

### Run tests in parallel (requires pytest-xdist)
```bash
pip install pytest-xdist
pytest tests/ -n auto  # Use all CPU cores
```

---

## Integration with IDE

### VS Code

Add to `settings.json`:
```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "backend/tests",
    "--cov=backend/app"
  ]
}
```

### PyCharm

1. Go to Settings → Tools → Python Integrated Tools
2. Set Default test runner to pytest
3. Tests will appear in Test Explorer

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.13
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests with coverage
        run: |
          cd backend && pytest tests/ --cov=backend/app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Questions?

Refer to:
- `TEST_GUIDE.md` - Comprehensive test documentation
- `TEST_REQUIREMENTS_CHECKLIST.md` - All requirements met
- Individual test files for examples
- `conftest_factories.py` for available data builders

---

**Generated**: 2024-03-25
**Updated**: 2024-03-25
**Version**: 1.0
