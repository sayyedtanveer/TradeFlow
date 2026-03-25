"""E2E test fixtures for full system workflow testing."""

import pytest
from uuid import uuid4


@pytest.fixture
def e2e_test_context(test_tenant_id, test_user_id):
    """Provide context for E2E tests including tenant and user IDs."""
    return {
        "tenant_id": test_tenant_id,
        "user_id": test_user_id,
        "product_template_id": None,
        "variant_ids": [],
        "bom_ids": [],
        "material_ids": [],
        "operation_ids": [],
    }
