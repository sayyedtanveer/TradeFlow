"""Stock Aggregation Service - Query product availability across warehouses.

Core responsibilities:
  - Aggregate inventory across all warehouses
  - Show which warehouses have a product in stock
  - Support client portal visibility of product availability
  - Support admin inventory planning
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Dict

from backend.app.domain.warehouse.repositories.warehouse_product_assignment_repository import (
    WarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class StockAggregationService:
    """Service for aggregating and querying product availability."""

    def __init__(
        self,
        warehouse_product_repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        """Initialize stock aggregation service."""
        self._warehouse_product_repo = warehouse_product_repo
        self._uow = uow

    async def get_product_availability(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> ProductAvailabilityInfo:
        """
        Get availability info for a product across all warehouses.

        Returns:
            ProductAvailabilityInfo with list of warehouses
        """
        assignments = await self._warehouse_product_repo.get_warehouses_for_product(
            product_id=product_id,
            tenant_id=tenant_id,
        )

        is_available_anywhere = len(assignments) > 0

        warehouse_list = [
            WarehouseAvailabilityInfo(
                warehouse_id=a.warehouse_id,
                is_available=a.is_available,
                default_reorder_level=a.default_reorder_level,
            )
            for a in assignments
        ]

        return ProductAvailabilityInfo(
            product_id=product_id,
            is_available_anywhere=is_available_anywhere,
            available_warehouse_count=len(warehouse_list),
            warehouses=warehouse_list,
        )

    async def get_products_for_warehouse(
        self,
        tenant_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> WarehouseInventoryInfo:
        """
        Get all products available at a specific warehouse.

        Returns:
            WarehouseInventoryInfo with product list
        """
        assignments = await self._warehouse_product_repo.get_products_for_warehouse(
            warehouse_id=warehouse_id,
            tenant_id=tenant_id,
        )

        product_list = [
            ProductInventoryInfo(
                product_id=a.product_id,
                is_available=a.is_available,
                default_reorder_level=a.default_reorder_level,
            )
            for a in assignments
        ]

        return WarehouseInventoryInfo(
            warehouse_id=warehouse_id,
            product_count=len(product_list),
            products=product_list,
        )

    async def get_warehouses_with_all_products(
        self,
        tenant_id: uuid.UUID,
        product_ids: List[uuid.UUID],
    ) -> List[uuid.UUID]:
        """
        Find warehouses that stock ALL products in the list.

        Used for order allocation and capability analysis.
        """
        if not product_ids:
            return []

        # Get warehouses for each product
        warehouse_sets = []
        for product_id in product_ids:
            assignments = await self._warehouse_product_repo.get_warehouses_for_product(
                product_id=product_id,
                tenant_id=tenant_id,
            )
            warehouse_ids = {a.warehouse_id for a in assignments}
            if not warehouse_ids:
                # If any product is unavailable, no warehouse has all
                return []
            warehouse_sets.append(warehouse_ids)

        # Find intersection
        if not warehouse_sets:
            return []

        result = warehouse_sets[0]
        for warehouse_set in warehouse_sets[1:]:
            result = result.intersection(warehouse_set)

        return list(result)

    async def get_coverage_analysis(
        self,
        tenant_id: uuid.UUID,
        product_ids: Optional[List[uuid.UUID]] = None,
    ) -> CoverageAnalysis:
        """
        Analyze product coverage across warehouses.

        Returns statistics about:
          - Products available in all warehouses
          - Products in only 1 warehouse
          - Products not available anywhere
          - Average warehouse coverage per product
        """
        # This would typically query inventory/material models for product list
        # For now, placeholder implementation

        return CoverageAnalysis(
            total_products=0,
            products_in_all_warehouses=0,
            products_in_single_warehouse=0,
            products_unavailable=0,
            average_warehouses_per_product=0.0,
        )


# ── DTOs ──────────────────────────────────────────────────────────────────────

class WarehouseAvailabilityInfo:
    """Info about product availability in a warehouse."""

    def __init__(
        self,
        warehouse_id: uuid.UUID,
        is_available: bool,
        default_reorder_level: int,
    ):
        self.warehouse_id = warehouse_id
        self.is_available = is_available
        self.default_reorder_level = default_reorder_level


class ProductAvailabilityInfo:
    """Info about product availability across warehouses."""

    def __init__(
        self,
        product_id: uuid.UUID,
        is_available_anywhere: bool,
        available_warehouse_count: int,
        warehouses: List[WarehouseAvailabilityInfo],
    ):
        self.product_id = product_id
        self.is_available_anywhere = is_available_anywhere
        self.available_warehouse_count = available_warehouse_count
        self.warehouses = warehouses


class ProductInventoryInfo:
    """Info about product in warehouse inventory."""

    def __init__(
        self,
        product_id: uuid.UUID,
        is_available: bool,
        default_reorder_level: int,
    ):
        self.product_id = product_id
        self.is_available = is_available
        self.default_reorder_level = default_reorder_level


class WarehouseInventoryInfo:
    """Info about warehouse inventory."""

    def __init__(
        self,
        warehouse_id: uuid.UUID,
        product_count: int,
        products: List[ProductInventoryInfo],
    ):
        self.warehouse_id = warehouse_id
        self.product_count = product_count
        self.products = products


class CoverageAnalysis:
    """Analysis of product coverage across warehouses."""

    def __init__(
        self,
        total_products: int,
        products_in_all_warehouses: int,
        products_in_single_warehouse: int,
        products_unavailable: int,
        average_warehouses_per_product: float,
    ):
        self.total_products = total_products
        self.products_in_all_warehouses = products_in_all_warehouses
        self.products_in_single_warehouse = products_in_single_warehouse
        self.products_unavailable = products_unavailable
        self.average_warehouses_per_product = average_warehouses_per_product
