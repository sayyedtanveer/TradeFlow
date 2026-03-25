import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.domain.bom.entities.bom import BillOfMaterial
from backend.app.domain.bom.services.bom_browser_service import BOMBrowserService, BOMProvider, ComponentDetailProvider
from backend.app.domain.bom.services.cost_rollup_service import CostRollupService, CostProvider
from backend.app.application.bom.queries.bom_advanced_queries import GetBOMTreeQuery, GetBOMCostQuery
from backend.app.infrastructure.services.bom_providers import (
    InfrastructureBOMProvider,
    InfrastructureCostProvider,
    InfrastructureComponentDetailProvider
)
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork


class BOMAdvancedHandlers:
    def __init__(self, uow: SQLAlchemyUnitOfWork, bom_repo):
        self._uow = uow
        self._bom_repo = bom_repo

    async def handle_get_tree(self, query: GetBOMTreeQuery) -> Dict[str, Any]:
        bom = await self._bom_repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")

        provider = InfrastructureBOMProvider(self._bom_repo)
        details = InfrastructureComponentDetailProvider(self._uow._session)
        service = BOMBrowserService(provider, details)
        
        tree = await service.build_tree(query.tenant_id, bom, max_depth=query.max_depth)
        
        # If parent_id is requested, find it in the tree and return it as root
        if query.parent_id and str(query.parent_id) != str(query.bom_id):
            return service.find_node_in_tree(tree, str(query.parent_id)) or {}
            
        return tree

    async def handle_get_cost(self, query: GetBOMCostQuery) -> Dict[str, Any]:
        bom = await self._bom_repo.get_by_id(query.bom_id, query.tenant_id)
        if not bom:
            raise ValueError(f"BOM {query.bom_id} not found.")

        bom_provider = InfrastructureBOMProvider(self._bom_repo)
        cost_provider = InfrastructureCostProvider(self._uow._session)
        service = CostRollupService(bom_provider, cost_provider)
        
        return await service.calculate_standard_cost(query.tenant_id, bom, max_depth=query.max_depth)
