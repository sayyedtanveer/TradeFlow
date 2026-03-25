# MedTrack Test Suite - Complete Guide

## Overview

This document describes the standardized, modular test suite for the MedTrack ERP system. The suite includes **156+ tests** covering unit, API, and end-to-end scenarios across all major modules.

---

## Test Structure

```
backend/tests/
├── conftest.py                    # Core fixtures (async_client, tokens, etc.)
├── conftest_factories.py          # Factory functions for test data
├── pytest.ini                      # Pytest configuration + coverage settings
│
├── unit/                           # Unit tests (pure logic, no DB)
│   ├── conftest.py                # Unit test shared fixtures
│   ├── product/
│   │   ├── conftest.py
│   │   └── test_product_domain.py       # 26 tests
│   ├── bom/
│   │   ├── conftest.py
│   │   └── test_bom_domain.py           # 30 tests
│   ├── operations/
│   │   ├── conftest.py
│   │   └── test_operations_domain.py    # 20 tests
│   └── inventory/
│       ├── conftest.py
│       └── test_inventory_domain.py     # 25 tests
│
├── api/                            # API integration tests
│   ├── conftest.py                # API test shared fixtures
│   ├── product/
│   │   ├── conftest.py
│   │   └── test_product_api.py           # 11 tests
│   ├── bom/
│   │   ├── conftest.py
│   │   └── test_bom_api.py               # 18 tests
│   └── operations/
│       ├── conftest.py
│       └── test_operations_api.py        # 16 tests
│
└── e2e/                            # End-to-end tests
    ├── conftest.py                # E2E shared fixtures
    └── test_full_bom_flow.py       # 11 E2E scenarios
```

---

## Running Tests

### Run all tests
```bash
cd backend
pytest tests/ -v
```

### Run tests by category

```bash
# Unit tests only
pytest tests/unit/ -v -m "not integration"

# API tests only
pytest tests/api/ -v

# E2E tests only
pytest tests/e2e/ -v

# Specific module
pytest tests/unit/bom/ -v
pytest tests/api/product/ -v
```

### Run with coverage

```bash
# Full coverage report
pytest tests/ --cov=backend/app --cov-report=term-missing

# HTML coverage report
pytest tests/ --cov=backend/app --cov-report=html
# View: htmlcov/index.html

# Coverage for specific module
pytest tests/unit/bom/ --cov=backend/app/domain/bom --cov-report=term-missing
```

### Run specific test

```bash
# Single test class
pytest tests/unit/bom/test_bom_domain.py::TestBOMCreation -v

# Single test method
pytest tests/api/bom/test_bom_api.py::TestBOMAPI::test_create_bom_success -v
```

---

## Test Categories

### Unit Tests (~100 tests)

Pure domain logic tests with no external dependencies. Each module includes:

**Product Module** (26 tests)
- Template creation and validation
- Variant generation and SKU management
- Attribute validation (text, allowed values)
- Duplicate prevention (code, variant key)
- Product equality

**BOM Module** (30 tests)
- BOM initialization and versioning
- Line item management (add, quantity validation)
- Scrap percentage calculation
- Circular dependency detection
- Cost aggregation and totaling
- Version control (increment, active BOM)

**Operations Module** (20 tests)
- Operation creation and process types
- Time and cost estimation
- Labor and equipment cost calculation
- Operation sequencing and dependencies
- Workstation management
- Soft delete behavior

**Inventory Module** (25 tests)
- Material creation and UOM
- Stock addition/removal
- Negative stock prevention
- Batch/lot tracking and expiration
- Stock reservation and release
- Stock adjustment history
- Soft delete behavior

### API Tests (~45 tests)

Integration tests for REST API endpoints. Each module includes:

**Product Endpoints**
- Create template (POST 201)
- Get template (GET 200/404)
- List templates (GET 200)
- Create variant (POST 201)
- List variants (GET 200)
- Validation errors (422)
- Unauthorized (401)
- Duplicate prevention (409)

**BOM Endpoints**
- Create BOM (POST 201)
- Get BOM (GET 200/404)
- List BOMs (GET 200)
- Add lines (POST 201)
- Remove lines (DELETE 204)
- Validate BOM (POST 200)
- Activate BOM (POST 200)
- Copy BOM (POST 201)
- Get tree (GET 200)
- Get costs (GET 200)
- Attach operations (POST 201)

**Operations Endpoints**
- Create operation (POST 201)
- Get operation (GET 200/404)
- List operations (GET 200)
- Update operation (PUT 200)
- Delete operation (DELETE 204)
- Create workstation (POST 201)
- Update workstation (PUT 200)
- Get cost (GET 200)

### E2E Tests (~11 scenarios)

Complete workflow tests simulating real user scenarios:

**Full BOM Flow (11 Steps)**
1. Create product template
2. Add attributes
3. Generate variants
4. Create BOM
5. Add components/materials
6. Validate BOM
7. Copy BOM to new version
8. Activate BOM
9. Add manufacturing operations
10. Fetch BOM tree structure
11. Calculate total costs

**Complex Scenarios**
- Multi-level BOM hierarchy
- Version control and activation
- Cost rollup and aggregation

**Error Handling**
- Circular dependency detection
- Invalid date ranges
- Invalid BOM activation

---

## Fixtures

### Core Fixtures (`conftest.py`)

```python
# Database
db_session: AsyncSession           # Test database session

# Authentication
token_headers: dict                # Auth headers with JWT
test_tenant_id: uuid.UUID          # Test tenant ID
test_user_id: uuid.UUID            # Test user ID
tenant_context: TenantContext      # Tenant context object

# API Clients
async_client: AsyncClient          # Async HTTP client (auto-injected DB)
authenticated_async_client         # Async client with auth headers
sync_client: TestClient            # Sync client for simple tests
authenticated_sync_client          # Sync client with auth headers

# Sample Data
sample_product_template: dict      # Product template fixture
sample_variant_data: dict          # Product variant fixture
sample_bom_create_payload: dict    # BOM creation payload
sample_operation_data: dict        # Operation data
sample_material_data: dict         # Material data
```

### Factory Functions (`conftest_factories.py`)

All factory functions return **payload dictionaries** ready for API calls:

```python
# User/Auth
create_user_data()
create_operation_payload()
create_workstation_payload()

# Products
create_product_template_payload()
create_product_variant_payload()

# BOMs
create_bom_payload()
create_bom_line_payload()
create_bom_with_lines_payload()

# Materials
create_material_payload()

# Inventory
create_stock_adjustment_payload()
create_batch_payload()

# Utilities
generate_uuid()
generate_test_id(prefix)
create_pagination_params()
create_error_response()
```

---

## Coverage Requirements

### Coverage Targets

- **Minimum Overall**: 80%
- **Minimum Per Module**: 75%
- **Configuration**: `pytest.ini` enforces `fail_under = 75`

### Coverage Report

```bash
# Generate coverage
pytest tests/ --cov=backend/app --cov-report=term-missing

# Output example:
# backend/app/domain/bom/entities/bom.py        85%
# backend/app/domain/product/ ...                82%
# backend/app/interfaces/api/v1/routes/boms.py  78%
# TOTAL: 81%  ✅ PASS (≥80%)
```

---

## Test Data & Isolation

### Test Database

- **Type**: SQLite in-memory (`:memory:`)
- **Isolation**: Each test gets fresh transaction
- **Cleanup**: Auto-rollback after each test
- **Advantages**: Fast, isolated, no external dependencies

### Test Credentials

```python
test_user_id  = "550e8400-e29b-41d4-a716-446655440000"
test_user_email = "test@medtrack-demo.com"
test_user_password = "TestPassword123!"
test_tenant_id = "b5ef68c4-18be-4fa6-a439-a23c34877550"
```

### Data Reuse Strategy

1. **Factories** instead of fixtures for flexible creation
2. **Module-level conftest** for shared test data
3. **Parametrized tests** for multiple scenarios
4. **Soft deletes** tested explicitly

---

## Test Naming Convention

### File Names
```
test_<feature>.py
test_product_domain.py
test_bom_api.py
test_full_bom_flow.py
```

### Class Names
```
Test<Feature>
TestProductTemplate
TestBOMLineItems
TestOperationsAPI
```

### Method Names
```
test_<specific_behavior>
test_create_product_template
test_add_bom_line_success
test_unauthorized_access_denied
```

---

## Test Markers

```python
@pytest.mark.unit        # Unit tests
@pytest.mark.api         # API tests
@pytest.mark.e2e         # E2E tests
@pytest.mark.asyncio     # Async tests
@pytest.mark.slow        # Slow tests
```

Usage:
```bash
pytest tests/ -m "unit"          # Run unit tests only
pytest tests/ -m "not slow"      # Exclude slow tests
```

---

## Continuous Integration

### GitHub Actions / CI Pipeline

```yaml
- pytest tests/ --cov=backend/app --cov-report=xml
- Fail if coverage < 80%
- Generate HTML report
- Comment on PR
```

---

## Common Test Patterns

### Testing Success Case

```python
async def test_create_bom_success(authenticated_async_client):
    payload = create_bom_payload()
    response = await authenticated_async_client.post(
        "/api/v1/boms",
        json=payload,
    )
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["id"]
```

### Testing Validation Error

```python
async def test_invalid_quantity_rejected(authenticated_async_client):
    payload = create_bom_line_payload(quantity=-1.0)
    response = await authenticated_async_client.post(
        "/api/v1/boms/123/lines",
        json=payload,
    )
    assert response.status_code == 422
```

### Testing Unauthorized

```python
async def test_unauthorized_denied(async_client):
    response = await async_client.get("/api/v1/boms")
    assert response.status_code in [401, 403]
```

### Testing Not Found

```python
async def test_nonexistent_bom_not_found(authenticated_async_client):
    response = await authenticated_async_client.get(
        f"/api/v1/boms/{uuid4()}"
    )
    assert response.status_code == 404
```

---

## Troubleshooting

### Fixture Not Found

```
ERROR E       fixture 'async_client' not found
```
**Solution**: Ensure `backend/tests/conftest.py` exists with `async_client` fixture.

### Asyncio Error

```
ERROR E       RuntimeError: Event loop is closed
```
**Solution**: Use `@pytest.mark.asyncio` and run with `pytest-asyncio`.

### Database Connection Error

```
ERROR E       sqlite3.OperationalError: database is locked
```
**Solution**: Tests use in-memory SQLite with StaticPool. Check fixture scope.

### Import Error

```
ERROR E       ImportError: No module named 'backend.app'
```
**Solution**: Ensure `backend/` has `__init__.py` and pytest runs from project root.

---

## Performance Benchmarks

| Category | Count | Typical Time |
|----------|-------|--------------|
| Unit Tests | ~100 | 2-3 seconds |
| API Tests | ~45 | 3-5 seconds |
| E2E Tests | ~11 | 2-3 seconds |
| **Total** | **~156** | **7-11 seconds** |

---

## Dependencies

```
pytest==8.2.0
pytest-asyncio==0.23.6
pytest-cov==5.0.0
httpx                  # For async HTTP client
sqlalchemy==2.1.0b1    # ORM and session management
```

---

## Best Practices

1. ✅ Use factories for flexible test data
2. ✅ Keep tests small and focused
3. ✅ Test edge cases (empty, negative, null)
4. ✅ Use parametrized tests for variations
5. ✅ Test error conditions explicitly
6. ✅ Avoid test interdependencies
7. ✅ Clean assertions (not overly specific)
8. ✅ Use meaningful test names

---

## Future Improvements

1. Performance optimization tests
2. Load/stress testing
3. Security-focused tests
4. Integration with real database
5. Property-based testing (hypothesis)
6. Contract testing with frontend
7. Test data builders for complex scenarios

---

## Questions & Support

For test-related questions, refer to:
- Individual test files for specific behavior
- `conftest_factories.py` for available test data builders
- `pytest.ini` for configuration details

---

**Generated**: 2024-03-25
**Version**: 1.0
**Test Count**: 156+
**Coverage Target**: 80%+
