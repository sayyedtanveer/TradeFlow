"""Warehouse command handlers (application orchestration)."""

from uuid import UUID

from backend.app.domain.warehouse.entities.warehouse import Warehouse
from backend.app.domain.warehouse.entities.warehouse_user_assignment import (
    WarehouseUserAssignment,
)
from backend.app.domain.warehouse.repositories.warehouse_repository import (
    WarehouseRepository,
)
from backend.app.domain.warehouse.repositories.warehouse_user_assignment_repository import (
    WarehouseUserAssignmentRepository,
)
from backend.app.domain.warehouse.value_objects import Address
from backend.app.application.warehouse.commands import (
    CreateWarehouseCommand,
    UpdateWarehouseCommand,
    DeactivateWarehouseCommand,
    AssignUserToWarehouseCommand,
    RemoveUserFromWarehouseCommand,
)


class CreateWarehouseCommandHandler:
    """Handler for creating new warehouses."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
    ):
        """Initialize handler."""
        self.warehouse_repo = warehouse_repo

    async def handle(self, command: CreateWarehouseCommand) -> UUID:
        """
        Create a new warehouse.

        Enforces unique warehouse name per tenant.

        Args:
            command: Create warehouse command

        Returns:
            The new warehouse ID

        Raises:
            ValueError: If warehouse name already exists within tenant
        """
        # Enforce unique name per tenant
        existing = await self.warehouse_repo.get_by_name(
            tenant_id=command.tenant_id,
            name=command.name,
        )
        if existing:
            raise ValueError(
                f"A warehouse with name '{command.name}' already exists in this tenant"
            )

        # Build address value object
        address = Address(
            street=command.address_street,
            city=command.address_city,
            region=command.address_region,
            postal_code=command.address_postal_code,
            country=command.address_country,
        )

        # Create warehouse aggregate
        warehouse = Warehouse(
            tenant_id=command.tenant_id,
            name=command.name,
            address=address,
            phone=command.phone,
            email=command.email,
        )

        # Persist
        saved = await self.warehouse_repo.save(warehouse)
        return saved.id


class UpdateWarehouseCommandHandler:
    """Handler for updating warehouse profiles."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
    ):
        """Initialize handler."""
        self.warehouse_repo = warehouse_repo

    async def handle(self, command: UpdateWarehouseCommand) -> None:
        """
        Update a warehouse's profile.

        Enforces unique warehouse name per tenant if name is being changed.

        Args:
            command: Update warehouse command

        Raises:
            ValueError: If warehouse not found or name conflict
        """
        warehouse = await self.warehouse_repo.get_by_id(
            id=command.warehouse_id,
            tenant_id=command.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {command.warehouse_id} not found")

        # If name is being changed, check uniqueness
        if command.name is not None and command.name != warehouse.name:
            existing = await self.warehouse_repo.get_by_name(
                tenant_id=command.tenant_id,
                name=command.name,
            )
            if existing:
                raise ValueError(
                    f"A warehouse with name '{command.name}' already exists in this tenant"
                )

        # Build address if any address field is provided
        new_address = None
        if any([
            command.address_street is not None,
            command.address_city is not None,
            command.address_region is not None,
            command.address_postal_code is not None,
            command.address_country is not None,
        ]):
            # Merge with existing address, overriding only provided fields
            current_addr = warehouse.address
            new_address = Address(
                street=command.address_street if command.address_street is not None else current_addr.street,
                city=command.address_city if command.address_city is not None else current_addr.city,
                region=command.address_region if command.address_region is not None else current_addr.region,
                postal_code=command.address_postal_code if command.address_postal_code is not None else current_addr.postal_code,
                country=command.address_country if command.address_country is not None else current_addr.country,
            )

        # Apply updates via domain method
        warehouse.update(
            name=command.name,
            address=new_address,
            phone=command.phone,
            email=command.email,
        )

        # Persist
        await self.warehouse_repo.save(warehouse)


class DeactivateWarehouseCommandHandler:
    """Handler for deactivating warehouses."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
    ):
        """Initialize handler."""
        self.warehouse_repo = warehouse_repo

    async def handle(self, command: DeactivateWarehouseCommand) -> None:
        """
        Deactivate a warehouse.

        Deactivated warehouses cannot receive new order assignments
        but allow completion of in-progress orders.

        Args:
            command: Deactivate warehouse command

        Raises:
            ValueError: If warehouse not found or already inactive
        """
        warehouse = await self.warehouse_repo.get_by_id(
            id=command.warehouse_id,
            tenant_id=command.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {command.warehouse_id} not found")

        # Domain method enforces already-inactive guard
        warehouse.deactivate()

        # Persist
        await self.warehouse_repo.save(warehouse)


class AssignUserToWarehouseCommandHandler:
    """Handler for assigning a user to a warehouse."""

    def __init__(
        self,
        warehouse_repo: WarehouseRepository,
        assignment_repo: WarehouseUserAssignmentRepository,
    ):
        """Initialize handler."""
        self.warehouse_repo = warehouse_repo
        self.assignment_repo = assignment_repo

    async def handle(self, command: AssignUserToWarehouseCommand) -> UUID:
        """
        Assign a user to a warehouse.

        Enforces single-warehouse-per-user invariant: if the user already
        has an assignment to a different warehouse, the previous assignment
        is revoked before creating the new one.

        Args:
            command: Assign user command

        Returns:
            The assignment ID

        Raises:
            ValueError: If warehouse not found or inactive
        """
        # Verify warehouse exists and is active
        warehouse = await self.warehouse_repo.get_by_id(
            id=command.warehouse_id,
            tenant_id=command.tenant_id,
        )
        if not warehouse:
            raise ValueError(f"Warehouse {command.warehouse_id} not found")
        if not warehouse.is_active:
            raise ValueError("Cannot assign users to an inactive warehouse")

        # Revoke any existing assignment for this user (single-warehouse invariant)
        existing_assignment = await self.assignment_repo.get_by_user_id(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
        )
        if existing_assignment:
            # If already assigned to the same warehouse, no-op
            if existing_assignment.warehouse_id == command.warehouse_id:
                return existing_assignment.id
            # Revoke previous assignment
            await self.assignment_repo.delete_by_user_id(
                tenant_id=command.tenant_id,
                user_id=command.user_id,
            )

        # Create new assignment
        assignment = WarehouseUserAssignment(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
            warehouse_id=command.warehouse_id,
            assigned_by=command.assigned_by,
        )

        saved = await self.assignment_repo.save(assignment)
        return saved.id


class RemoveUserFromWarehouseCommandHandler:
    """Handler for removing a user from a warehouse."""

    def __init__(
        self,
        assignment_repo: WarehouseUserAssignmentRepository,
    ):
        """Initialize handler."""
        self.assignment_repo = assignment_repo

    async def handle(self, command: RemoveUserFromWarehouseCommand) -> None:
        """
        Remove a user's warehouse assignment.

        Args:
            command: Remove user command

        Raises:
            ValueError: If user is not assigned to the specified warehouse
        """
        existing = await self.assignment_repo.get_by_user_id(
            tenant_id=command.tenant_id,
            user_id=command.user_id,
        )
        if not existing:
            raise ValueError(
                f"User {command.user_id} is not assigned to any warehouse"
            )
        if existing.warehouse_id != command.warehouse_id:
            raise ValueError(
                f"User {command.user_id} is not assigned to warehouse {command.warehouse_id}"
            )

        await self.assignment_repo.delete(
            id=existing.id,
            tenant_id=command.tenant_id,
        )
