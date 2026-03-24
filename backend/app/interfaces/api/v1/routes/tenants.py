from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_role
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.interfaces.api.v1.schemas.tenant_schemas import TenantResponse
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
    summary="Get tenant details (admin only)",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = TenantRepository(session)
        tenant = await repo.get_by_id(tenant_id, tenant_id)

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    return TenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        is_active=tenant.is_active,
    )
