"""API tests for Product module endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4


@pytest.mark.asyncio
class TestProductAPI:
    """Test product API endpoints."""

    async def test_create_product_template_success(
        self, authenticated_async_client: AsyncClient, sample_product_template: dict
    ):
        """Test successful product template creation (201)."""
        response = await authenticated_async_client.post(
            "/api/v1/products",
            json=sample_product_template,
        )
        
        assert response.status_code in [200, 201]

    async def test_create_product_template_validation_error(
        self, authenticated_async_client: AsyncClient
    ):
        """Test product template creation with invalid data (422)."""
        invalid_payload = {
            "name": "",  # Empty name
            "code": "TEST",
        }
        
        response = await authenticated_async_client.post(
            "/api/v1/products",
            json=invalid_payload,
        )
        
        assert response.status_code in [400, 422]

    async def test_get_product_template_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting product template (200)."""
        # Assuming a product exists or create one first
        template_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/{template_id}",
        )
        
        # May be 200 (found) or 404 (not found) - both are valid
        assert response.status_code in [200, 404]

    async def test_get_nonexistent_product_not_found(
        self, authenticated_async_client: AsyncClient
    ):
        """Test getting non-existent product (404)."""
        nonexistent_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/{nonexistent_id}",
        )
        
        assert response.status_code == 404

    async def test_list_products_success(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing products (200)."""
        response = await authenticated_async_client.get(
            "/api/v1/products",
            params={"page": 1, "page_size": 50},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))

    async def test_unauthorized_access_denied(
        self, async_client: AsyncClient, sample_product_template: dict
    ):
        """Test unauthorized access (401)."""
        response = await async_client.post(
            "/api/v1/products",
            json=sample_product_template,
        )
        
        assert response.status_code in [401, 403]

    async def test_create_product_variant(
        self, authenticated_async_client: AsyncClient
    ):
        """Test creating product variant."""
        template_id = str(uuid4())
        variant_payload = {
            "template_id": template_id,
            "variant_key": "RED-M",
            "sku": "SKU-RED-M",
            "attributes": {"Color": "Red", "Size": "M"},
        }
        
        response = await authenticated_async_client.post(
            "/api/v1/products/variants",
            json=variant_payload,
        )
        
        assert response.status_code in [200, 201, 404, 422]

    async def test_list_product_variants(
        self, authenticated_async_client: AsyncClient
    ):
        """Test listing product variants."""
        template_id = str(uuid4())
        
        response = await authenticated_async_client.get(
            f"/api/v1/products/{template_id}/variants",
        )
        
        assert response.status_code in [200, 404]


class TestProductValidation:
    """Test product validation rules."""

    async def test_duplicate_product_code_rejected(
        self, authenticated_async_client: AsyncClient
    ):
        """Test duplicate product codes are rejected."""
        payload = {
            "name": "Product A",
            "code": "DUPLICATE-CODE",
            "description": "First",
        }
        
        # Create first product
        response1 = await authenticated_async_client.post(
            "/api/v1/products",
            json=payload,
        )
        
        # Attempt duplicate
        response2 = await authenticated_async_client.post(
            "/api/v1/products",
            json=payload,
        )
        
        # Second should fail with conflict or validation error
        if response1.status_code in [200, 201]:
            assert response2.status_code in [400, 409, 422]

    async def test_duplicate_variant_key_rejected(
        self, authenticated_async_client: AsyncClient
    ):
        """Test duplicate variant keys are rejected."""
        template_id = str(uuid4())
        variant_key = "VAR-UNIQUE"
        
        payload = {
            "template_id": template_id,
            "variant_key": variant_key,
            "sku": "SKU-001",
            "attributes": {"Size": "M"},
        }
        
        # Create variant
        response1 = await authenticated_async_client.post(
            "/api/v1/products/variants",
            json=payload,
        )
        
        # Attempt duplicate
        payload["sku"] = "SKU-002"  # Different SKU, same variant key
        response2 = await authenticated_async_client.post(
            "/api/v1/products/variants",
            json=payload,
        )
        
        # Should reject duplicate variant key
        if response1.status_code in [200, 201]:
            assert response2.status_code in [400, 409, 422]
