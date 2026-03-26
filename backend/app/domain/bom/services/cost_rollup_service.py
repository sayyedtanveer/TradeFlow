import uuid
from decimal import Decimal
from typing import Optional, Protocol, Dict, Any, Tuple

from backend.app.domain.bom.entities.bom import BillOfMaterial


class BOMProvider(Protocol):
    async def get_active_bom(
        self, tenant_id: uuid.UUID, template_id: Optional[uuid.UUID] = None, variant_id: Optional[uuid.UUID] = None
    ) -> Optional[BillOfMaterial]:
        ...


class CostProvider(Protocol):
    async def get_material_cost(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
        ...

    async def get_operation_cost(self, tenant_id: uuid.UUID, operation_id: uuid.UUID) -> Decimal:
        """Returns the hourly rate or cost-per-minute of the operation's workstation."""
        ...


class CostRollupService:
    def __init__(self, bom_provider: BOMProvider, cost_provider: CostProvider):
        self._bom_provider = bom_provider
        self._cost_provider = cost_provider

    async def calculate_standard_cost(
        self, tenant_id: uuid.UUID, current_bom: BillOfMaterial, max_depth: int = 20
    ) -> Dict[str, Any]:
        """
        Calculates the complete rolled-up cost of a BOM entirely in the domain layer.
        Cost = Sum of materials + Sum of operations.
        Returns a structured dictionary:
        {
            "material_cost": <Decimal>,
            "operation_cost": <Decimal>,
            "total_cost": <Decimal>,
            "currency": "USD"
        }
        """
        mat, op, tot = await self._calculate_recursive(tenant_id, current_bom, depth=1, max_depth=max_depth)
        return {
            "material_cost": mat,
            "operation_cost": op,
            "total_cost": tot,
            "currency": "USD",
        }

    async def _calculate_recursive(
        self, tenant_id: uuid.UUID, bom: BillOfMaterial, depth: int, max_depth: int
    ) -> Tuple[Decimal, Decimal, Decimal]:
        if depth > max_depth:
            raise ValueError(f"Max depth of {max_depth} reached during cost rollup.")

        material_cost_total = Decimal('0.00')
        operation_cost_total = Decimal('0.00')

        # 1. Add Material Costs
        for line in bom.lines:
            line_qty = Decimal(str(line.quantity))
            if line.scrap_percentage > 0:
                line_qty = line_qty * (Decimal('1') + Decimal(str(line.scrap_percentage)) / Decimal('100'))

            unit_cost = Decimal('0.0000')
            if line.material_id:
                unit_cost = await self._cost_provider.get_material_cost(tenant_id, line.material_id)
            elif line.template_id or line.variant_id:
                child_bom = await self._bom_provider.get_active_bom(
                    tenant_id=tenant_id, template_id=line.template_id, variant_id=line.variant_id
                )
                if child_bom:
                    _, _, child_cost = await self._calculate_recursive(tenant_id, child_bom, depth + 1, max_depth)
                    unit_cost = child_cost
                else:
                    unit_cost = Decimal('0.00')

            material_cost_total += line_qty * unit_cost

        # 2. Add Operation Costs
        for bom_op in bom.operations:
            op_total_cost = await self._cost_provider.get_operation_cost(tenant_id, bom_op.operation_id)
            operation_cost_total += op_total_cost

        return material_cost_total, operation_cost_total, (material_cost_total + operation_cost_total)
