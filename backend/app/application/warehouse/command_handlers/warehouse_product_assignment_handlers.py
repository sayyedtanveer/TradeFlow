"""Warehouse-Product Assignment Command Handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from backend.app.application.warehouse.commands.warehouse_product_assignment_commands import (
    AssignProductToWarehouseCommand,
    UnassignProductFromWarehouseCommand,
    MarkProductUnavailableCommand,
    MarkProductAvailableCommand,
    UpdateReorderLevelCommand,
)
from backend.app.domain.warehouse.entities.warehouse_product_assignment import (
    WarehouseProductAssignment,
)
from backend.app.domain.warehouse.repositories.warehouse_product_assignment_repository import (
    WarehouseProductAssignmentRepository,
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class WarehouseProductAssignmentResult:
    id: str
    tenant_id: str
    warehouse_id: str
    product_id: str
    is_available: bool
    default_reorder_level: int


# ── Command Handlers ──────────────────────────────────────────────────────────

class AssignProductToWarehouseCommandHandler:
    """Handler for AssignProductToWarehouseCommand."""

    def __init__(
        self,
        repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._repo = repo
        self._uow = uow

    async def handle(
        self, cmd: AssignProductToWarehouseCommand
    ) -> WarehouseProductAssignmentResult:
        """Assign a product to a warehouse or update existing assignment."""
        # Check if assignment already exists
        existing = await self._repo.get_by_warehouse_and_product(
            warehouse_id=cmd.warehouse_id,
            product_id=cmd.product_id,
            tenant_id=cmd.tenant_id,
        )

        if existing:
            # If it exists but is marked unavailable, re-enable it
            if not existing.is_available:
                existing.mark_available()
                existing.default_reorder_level = cmd.default_reorder_level
            else:
                # Update reorder level if already available
                existing.default_reorder_level = cmd.default_reorder_level
            assignment = await self._repo.save(existing)
        else:
            # Create new assignment
            assignment = WarehouseProductAssignment(
                id=uuid.uuid4(),
                tenant_id=cmd.tenant_id,
                warehouse_id=cmd.warehouse_id,
                product_id=cmd.product_id,
                is_available=True,
                default_reorder_level=cmd.default_reorder_level,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            assignment = await self._repo.save(assignment)

        await self._uow.commit()

        return WarehouseProductAssignmentResult(
            id=str(assignment.id),
            tenant_id=str(assignment.tenant_id),
            warehouse_id=str(assignment.warehouse_id),
            product_id=str(assignment.product_id),
            is_available=assignment.is_available,
            default_reorder_level=assignment.default_reorder_level,
        )


class UnassignProductFromWarehouseCommandHandler:
    """Handler for UnassignProductFromWarehouseCommand."""

    def __init__(
        self,
        repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._repo = repo
        self._uow = uow

    async def handle(self, cmd: UnassignProductFromWarehouseCommand) -> None:
        """Remove a product from a warehouse (soft delete)."""
        assignment = await self._repo.get_by_warehouse_and_product(
            warehouse_id=cmd.warehouse_id,
            product_id=cmd.product_id,
            tenant_id=cmd.tenant_id,
        )

        if not assignment:
            raise ValueError(
                f"Product {cmd.product_id} is not assigned to warehouse {cmd.warehouse_id}"
            )

        await self._repo.delete(assignment.id, cmd.tenant_id)
        await self._uow.commit()


class MarkProductUnavailableCommandHandler:
    """Handler for MarkProductUnavailableCommand."""

    def __init__(
        self,
        repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._repo = repo
        self._uow = uow

    async def handle(self, cmd: MarkProductUnavailableCommand) -> WarehouseProductAssignmentResult:
        """Mark a product as unavailable in a warehouse."""
        assignment = await self._repo.get_by_warehouse_and_product(
            warehouse_id=cmd.warehouse_id,
            product_id=cmd.product_id,
            tenant_id=cmd.tenant_id,
        )

        if not assignment:
            raise ValueError(
                f"Product {cmd.product_id} is not assigned to warehouse {cmd.warehouse_id}"
            )

        assignment.mark_unavailable()
        assignment = await self._repo.save(assignment)
        await self._uow.commit()

        return WarehouseProductAssignmentResult(
            id=str(assignment.id),
            tenant_id=str(assignment.tenant_id),
            warehouse_id=str(assignment.warehouse_id),
            product_id=str(assignment.product_id),
            is_available=assignment.is_available,
            default_reorder_level=assignment.default_reorder_level,
        )


class MarkProductAvailableCommandHandler:
    """Handler for MarkProductAvailableCommand."""

    def __init__(
        self,
        repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._repo = repo
        self._uow = uow

    async def handle(self, cmd: MarkProductAvailableCommand) -> WarehouseProductAssignmentResult:
        """Mark a product as available in a warehouse."""
        assignment = await self._repo.get_by_warehouse_and_product(
            warehouse_id=cmd.warehouse_id,
            product_id=cmd.product_id,
            tenant_id=cmd.tenant_id,
        )

        if not assignment:
            raise ValueError(
                f"Product {cmd.product_id} is not assigned to warehouse {cmd.warehouse_id}"
            )

        assignment.mark_available()
        assignment = await self._repo.save(assignment)
        await self._uow.commit()

        return WarehouseProductAssignmentResult(
            id=str(assignment.id),
            tenant_id=str(assignment.tenant_id),
            warehouse_id=str(assignment.warehouse_id),
            product_id=str(assignment.product_id),
            is_available=assignment.is_available,
            default_reorder_level=assignment.default_reorder_level,
        )


class UpdateReorderLevelCommandHandler:
    """Handler for UpdateReorderLevelCommand."""

    def __init__(
        self,
        repo: WarehouseProductAssignmentRepository,
        uow: SQLAlchemyUnitOfWork,
    ) -> None:
        self._repo = repo
        self._uow = uow

    async def handle(self, cmd: UpdateReorderLevelCommand) -> WarehouseProductAssignmentResult:
        """Update default reorder level for warehouse-product combo."""
        assignment = await self._repo.get_by_warehouse_and_product(
            warehouse_id=cmd.warehouse_id,
            product_id=cmd.product_id,
            tenant_id=cmd.tenant_id,
        )

        if not assignment:
            raise ValueError(
                f"Product {cmd.product_id} is not assigned to warehouse {cmd.warehouse_id}"
            )

        assignment.default_reorder_level = cmd.default_reorder_level
        assignment = await self._repo.save(assignment)
        await self._uow.commit()

        return WarehouseProductAssignmentResult(
            id=str(assignment.id),
            tenant_id=str(assignment.tenant_id),
            warehouse_id=str(assignment.warehouse_id),
            product_id=str(assignment.product_id),
            is_available=assignment.is_available,
            default_reorder_level=assignment.default_reorder_level,
        )
