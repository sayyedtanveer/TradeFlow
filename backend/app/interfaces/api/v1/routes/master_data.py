from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import List, Optional

import uuid

from sqlalchemy import select

from backend.app.interfaces.api.v1.dependencies.auth import get_current_tenant_id, get_container
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork

from backend.app.infrastructure.persistence.repositories.material_category_repository import MaterialCategoryRepository
from backend.app.infrastructure.persistence.repositories.location_repository import LocationRepository
from backend.app.infrastructure.persistence.repositories.unit_of_measure_repository import UnitOfMeasureRepository

from backend.app.domain.inventory.entities.material_category import MaterialCategory
from backend.app.domain.inventory.entities.location import Location, LocationType
from backend.app.domain.inventory.entities.unit_of_measure import UnitOfMeasure

from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.interfaces.api.v1.schemas.master_data_schemas import (
    CreateCategoryRequest,
    CategoryResponse,
    CreateLocationRequest,
    LocationResponse,
    CreateUnitRequest,
    UnitResponse,
    UpdateLocationRequest,
)

router = APIRouter(prefix="/inventory/master-data", tags=["Inventory Master Data"])


def _location_to_response(loc: Location) -> LocationResponse:
    lt = loc.location_type
    return LocationResponse(
        id=loc.id,
        tenant_id=loc.tenant_id,
        name=loc.name,
        code=loc.code,
        location_type=lt.value if hasattr(lt, "value") else str(lt),
        parent_location_id=loc.parent_location_id,
        is_active=loc.is_active,
    )


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

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("inventory:write"))])
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
    type: Optional[str] = Query(None, description="Filter by location type (e.g. quarantine)"),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        if type is not None:
            stmt = (
                select(LocationModel)
                .where(
                    LocationModel.tenant_id == tenant_id,
                    LocationModel.is_deleted.is_(False),
                    LocationModel.type == type,
                )
                .order_by(LocationModel.name.asc())
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            locations = [repo._to_entity(m) for m in models]
        else:
            locations = await repo.list(tenant_id, page_size=500)
    return [_location_to_response(loc) for loc in locations]

@router.post(
    "/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def create_location(
    req: CreateLocationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    try:
        lt = LocationType(req.type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location type")
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)

        location = Location(
            tenant_id=tenant_id,
            name=req.name,
            location_type=lt,
            parent_location_id=req.parent_id,
            code=req.code,
            is_active=req.is_active,
        )

        await repo.save(location)
        await uow.commit()
    return _location_to_response(location)


@router.put(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("inventory:write"))],
)
async def update_location(
    location_id: uuid.UUID,
    req: UpdateLocationRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    container = get_container(request)
    async with container.session_factory() as session:
        repo = LocationRepository(session)
        uow = SQLAlchemyUnitOfWork(session=session, event_dispatcher=container.event_dispatcher)
        location = await repo.get_by_id(location_id, tenant_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        if req.name is not None:
            location.name = req.name
        if req.code is not None:
            location.code = req.code
        if req.parent_id is not None:
            location.parent_location_id = req.parent_id
        if req.is_active is not None:
            location.is_active = req.is_active
        await repo.save(location)
        await uow.commit()
    return _location_to_response(location)

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

@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("inventory:write"))])
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
