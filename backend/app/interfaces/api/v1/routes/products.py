from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.application.product.commands.product_commands import (
    CreateItemTemplateCommand,
    UpdateItemTemplateCommand,
    CreateItemVariantCommand,
    UpdateItemVariantCommand,
)
from backend.app.application.product.handlers.product_handlers import (
    CreateItemTemplateHandler,
    UpdateItemTemplateHandler,
    CreateItemVariantHandler,
    UpdateItemVariantHandler,
)
from backend.app.application.product.handlers.product_query_handler import ProductQueryHandler
from backend.app.application.product.queries.product_queries import (
    GetItemTemplateQuery,
    ListItemTemplatesQuery,
    GetItemVariantQuery,
    ListItemVariantsQuery,
)
from backend.app.infrastructure.persistence.repositories.item_template_repository import ItemTemplateRepository
from backend.app.infrastructure.persistence.repositories.item_variant_repository import ItemVariantRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.schemas.product_schemas import (
    CreateItemTemplateRequest,
    UpdateItemTemplateRequest,
    ItemTemplateResponse,
    ItemTemplateListResponse,
    CreateItemVariantRequest,
    UpdateItemVariantRequest,
    ItemVariantResponse,
    ItemVariantListResponse,
)

router = APIRouter(prefix="/products", tags=["Product Master"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build repositories from session
# ─────────────────────────────────────────────────────────────────────────────

def _template_from_result(r) -> ItemTemplateResponse:
    return ItemTemplateResponse(
        id=uuid.UUID(r.id),
        tenant_id=uuid.UUID(r.tenant_id),
        code=r.code,
        name=r.name,
        description=r.description,
        category_id=uuid.UUID(r.category_id) if r.category_id else None,
        base_unit_id=uuid.UUID(r.base_unit_id) if r.base_unit_id else None,
        attributes=r.attributes,
        is_active=r.is_active,
    )


def _variant_from_result(r) -> ItemVariantResponse:
    from decimal import Decimal
    return ItemVariantResponse(
        id=uuid.UUID(r.id),
        tenant_id=uuid.UUID(r.tenant_id),
        template_id=uuid.UUID(r.template_id),
        code=r.code,
        name=r.name,
        variant_key=r.variant_key,
        attribute_values=r.attribute_values,
        base_unit_id=uuid.UUID(r.base_unit_id) if r.base_unit_id else None,
        standard_cost=Decimal(r.standard_cost),
        selling_price=Decimal(r.selling_price) if r.selling_price else None,
        is_active=r.is_active,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Item Template endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates",
    response_model=ItemTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Item Template",
)
async def create_template(
    body: CreateItemTemplateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateItemTemplateHandler(template_repo=repo, uow=uow)
        try:
            result = await handler.handle(
                CreateItemTemplateCommand(
                    tenant_id=tenant_id,
                    created_by=user_id,
                    code=body.code,
                    name=body.name,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    attributes=[a.model_dump() for a in body.attributes],
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return _template_from_result(result)


@router.get(
    "/templates",
    response_model=ItemTemplateListResponse,
    summary="List all Item Templates",
)
async def list_templates(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    query: Optional[str] = Query(None, description="Search by name or code"),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.list_templates(
            ListItemTemplatesQuery(
                tenant_id=tenant_id,
                query=query,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )
    return ItemTemplateListResponse(
        items=[_template_from_result(t) for t in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/templates/{template_id}",
    response_model=ItemTemplateResponse,
    summary="Get a single Item Template by ID",
)
async def get_template(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.get_template(GetItemTemplateQuery(id=template_id, tenant_id=tenant_id))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item template not found")
    return _template_from_result(result)


@router.put(
    "/templates/{template_id}",
    response_model=ItemTemplateResponse,
    summary="Update an Item Template",
)
async def update_template(
    template_id: uuid.UUID,
    body: UpdateItemTemplateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = ItemTemplateRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateItemTemplateHandler(template_repo=repo, uow=uow)
        try:
            result = await handler.handle(
                UpdateItemTemplateCommand(
                    id=template_id,
                    tenant_id=tenant_id,
                    name=body.name,
                    description=body.description,
                    category_id=body.category_id,
                    base_unit_id=body.base_unit_id,
                    attributes=[a.model_dump() for a in body.attributes] if body.attributes is not None else None,
                    is_active=body.is_active,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _template_from_result(result)


# ─────────────────────────────────────────────────────────────────────────────
# Item Variant endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/templates/{template_id}/variants",
    response_model=ItemVariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a variant for a template",
)
async def create_variant(
    template_id: uuid.UUID,
    body: CreateItemVariantRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = CreateItemVariantHandler(template_repo=t_repo, variant_repo=v_repo, uow=uow)
        try:
            result = await handler.handle(
                CreateItemVariantCommand(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    created_by=user_id,
                    attribute_values=body.attribute_values,
                    base_unit_id=body.base_unit_id,
                    standard_cost=body.standard_cost,
                    selling_price=body.selling_price,
                )
            )
        except ValueError as e:
            code = status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=code, detail=str(e))
    return _variant_from_result(result)


@router.get(
    "/templates/{template_id}/variants",
    response_model=ItemVariantListResponse,
    summary="List all variants for a template",
)
async def list_variants(
    template_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.list_variants(
            ListItemVariantsQuery(
                template_id=template_id,
                tenant_id=tenant_id,
                is_active=is_active,
                page=page,
                page_size=page_size,
            )
        )
    return ItemVariantListResponse(
        items=[_variant_from_result(v) for v in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/variants/{variant_id}",
    response_model=ItemVariantResponse,
    summary="Get a single variant by ID",
)
async def get_variant(
    variant_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        t_repo = ItemTemplateRepository(session)
        v_repo = ItemVariantRepository(session)
        handler = ProductQueryHandler(template_repo=t_repo, variant_repo=v_repo)
        result = await handler.get_variant(GetItemVariantQuery(id=variant_id, tenant_id=tenant_id))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item variant not found")
    return _variant_from_result(result)


@router.put(
    "/variants/{variant_id}",
    response_model=ItemVariantResponse,
    summary="Update variant pricing and status",
)
async def update_variant(
    variant_id: uuid.UUID,
    body: UpdateItemVariantRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        v_repo = ItemVariantRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        handler = UpdateItemVariantHandler(variant_repo=v_repo, uow=uow)
        try:
            result = await handler.handle(
                UpdateItemVariantCommand(
                    id=variant_id,
                    tenant_id=tenant_id,
                    standard_cost=body.standard_cost,
                    selling_price=body.selling_price,
                    is_active=body.is_active,
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _variant_from_result(result)
