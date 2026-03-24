from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

import uuid

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id
from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from fastapi import Request
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

from backend.app.infrastructure.persistence.repositories.material_category_repository import MaterialCategoryRepository
from backend.app.infrastructure.persistence.repositories.location_repository import LocationRepository
from backend.app.infrastructure.persistence.repositories.unit_of_measure_repository import UnitOfMeasureRepository

from backend.app.domain.inventory.entities.material_category import MaterialCategory
from backend.app.domain.inventory.entities.location import Location
from backend.app.domain.inventory.entities.unit_of_measure import UnitOfMeasure

from backend.app.interfaces.api.v1.schemas.master_data_schemas import (
    CreateCategoryRequest, CategoryResponse,
    CreateLocationRequest, LocationResponse,
    CreateUnitRequest, UnitResponse
)

router = APIRouter(prefix="/inventory/master-data", tags=["Inventory Master Data"])

# ── Categories ────────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        categories = await repo.list(tenant_id, page_size=100)
    return categories

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    req: CreateCategoryRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = MaterialCategoryRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        category = MaterialCategory(
            tenant_id=tenant_id,
            name=req.name,
            description=req.description,
            is_active=req.is_active,
        )
        
        await repo.save(category)
        await uow.commit()
    return category

# ── Locations ─────────────────────────────────────────────────────────────

@router.get("/locations", response_model=List[LocationResponse])
async def list_locations(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        locations = await repo.list(tenant_id, page_size=100)
    return locations

@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    req: CreateLocationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        location = Location(
            tenant_id=tenant_id,
            name=req.name,
            location_type=req.type,
            parent_location_id=req.parent_id,
            is_active=req.is_active,
        )
        
        await repo.save(location)
        await uow.commit()
    return location

# ── Units of Measure ──────────────────────────────────────────────────────

@router.get("/units", response_model=List[UnitResponse])
async def list_units(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        units = await repo.list(tenant_id, page_size=100)
    return units

@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(
    req: CreateUnitRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = UnitOfMeasureRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        
        unit = UnitOfMeasure(
            tenant_id=tenant_id,
            code=req.code,
            name=req.name,
            is_active=req.is_active,
        )
        
        await repo.save(unit)
        await uow.commit()
    return unit
