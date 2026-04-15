from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from backend.app.infrastructure.persistence.models.inventory_management_models import (
    StockReservationModel,
    WarehouseZoneModel,
    StockLedgerModel,
)
from backend.app.infrastructure.persistence.models.location_model import LocationModel
from backend.app.infrastructure.persistence.models.material_model import MaterialModel
from backend.app.infrastructure.persistence.repositories.material_repository import MaterialRepository
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_tenant_id,
    get_current_user_id,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_permission

router = APIRouter(prefix="/inventory", tags=["Inventory Extended"])

# ── Schemas ─────────────────────────────────────────────────────────────

class WarehouseZoneCreate(BaseModel):
    warehouse_location_id: uuid.UUID
    zone_name: str
    zone_type: str
    capacity: Optional[float] = None

class WarehouseZoneResponse(WarehouseZoneCreate):
    id: uuid.UUID
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class StockReservationCreate(BaseModel):
    material_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    quantity: float
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

class StockReservationResponse(StockReservationCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StockLedgerResponse(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    location_id: Optional[uuid.UUID]
    transaction_date: datetime
    transaction_type: str
    quantity_change: float
    running_balance: float
    reference_type: Optional[str]
    reference_id: Optional[uuid.UUID]
    model_config = ConfigDict(from_attributes=True)

class RealtimeStockResponse(BaseModel):
    material_id: uuid.UUID
    material_code: str
    material_name: str
    current_stock: float
    reserved_stock: float
    available_stock: float
    model_config = ConfigDict(from_attributes=True)

# ── Warehouse Zones ─────────────────────────────────────────────────────────

@router.post("/zones", response_model=WarehouseZoneResponse, dependencies=[Depends(require_permission("inventory:write"))])
async def create_warehouse_zone(
    body: WarehouseZoneCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        # verify the location is a warehouse
        loc = await session.get(LocationModel, body.warehouse_location_id)
        if not loc or loc.tenant_id != tenant_id or loc.type != "warehouse":
            raise HTTPException(status_code=400, detail="Invalid warehouse location")

        zone = WarehouseZoneModel(
            tenant_id=tenant_id,
            warehouse_location_id=body.warehouse_location_id,
            zone_name=body.zone_name,
            zone_type=body.zone_type,
            capacity=body.capacity
        )
        session.add(zone)
        await session.commit()
        await session.refresh(zone)
        return WarehouseZoneResponse.model_validate(zone)

@router.get("/zones", response_model=List[WarehouseZoneResponse])
async def list_warehouse_zones(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    warehouse_id: Optional[uuid.UUID] = Query(None)
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(WarehouseZoneModel).where(WarehouseZoneModel.tenant_id == tenant_id)
        if warehouse_id:
            stmt = stmt.where(WarehouseZoneModel.warehouse_location_id == warehouse_id)
        
        result = await session.execute(stmt)
        zones = result.scalars().all()
        return [WarehouseZoneResponse.model_validate(z) for z in zones]

# ── Reservations ────────────────────────────────────────────────────────────

@router.post("/reservations", response_model=StockReservationResponse, dependencies=[Depends(require_permission("inventory:write"))])
async def reserve_stock(
    body: StockReservationCreate,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        material_repo = MaterialRepository(session)
        material = await material_repo.get_by_id(body.material_id, tenant_id)
        if not material:
            raise HTTPException(404, "Material not found")
        
        try:
            material.reserve_stock(body.quantity)
        except ValueError as e:
            raise HTTPException(400, str(e))
        
        res = StockReservationModel(
            tenant_id=tenant_id,
            material_id=body.material_id,
            location_id=body.location_id,
            quantity=body.quantity,
            reference_type=body.reference_type,
            reference_id=body.reference_id,
            notes=body.notes,
            status="ACTIVE"
        )
        session.add(res)
        await material_repo.save(material)
        await session.commit()
        await session.refresh(res)
        return StockReservationResponse.model_validate(res)

@router.post("/reservations/{reservation_id}/consume", dependencies=[Depends(require_permission("inventory:write"))])
async def consume_reservation(
    reservation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        res = await session.get(StockReservationModel, reservation_id)
        if not res or res.tenant_id != tenant_id:
            raise HTTPException(404, "Reservation not found")
        if res.status != "ACTIVE":
            raise HTTPException(400, f"Reservation is {res.status}")
        
        material_repo = MaterialRepository(session)
        material = await material_repo.get_by_id(res.material_id, tenant_id)
        
        material.release_stock(res.quantity)
        material.decrease_stock(res.quantity) # Now decrease the actual stock
        
        # We should logically emit an OUT transaction, but simplified here
        ledger_entry = StockLedgerModel(
            tenant_id=tenant_id,
            material_id=material.id,
            location_id=res.location_id,
            transaction_date=datetime.now(),
            transaction_type="CONSUME_RESERVATION",
            quantity_change=-res.quantity,
            running_balance=material.get_available_stock(),
            reference_type=res.reference_type,
            reference_id=res.reference_id
        )
        session.add(ledger_entry)

        res.status = "CONSUMED"
        await material_repo.save(material)
        await session.commit()
        return {"status": "success"}

@router.post("/reservations/{reservation_id}/cancel", dependencies=[Depends(require_permission("inventory:write"))])
async def cancel_reservation(
    reservation_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        res = await session.get(StockReservationModel, reservation_id)
        if not res or res.tenant_id != tenant_id:
            raise HTTPException(404, "Reservation not found")
        if res.status != "ACTIVE":
            raise HTTPException(400, f"Reservation is {res.status}")
        
        material_repo = MaterialRepository(session)
        material = await material_repo.get_by_id(res.material_id, tenant_id)
        
        material.release_stock(res.quantity)
        res.status = "CANCELLED"
        
        await material_repo.save(material)
        await session.commit()
        return {"status": "success"}


# ── Ledger and Realtime ─────────────────────────────────────────────────────

@router.get("/ledger", response_model=List[StockLedgerResponse])
async def get_stock_ledger(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    material_id: Optional[uuid.UUID] = Query(None),
    limit: int = 100
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(StockLedgerModel).where(StockLedgerModel.tenant_id == tenant_id)
        if material_id:
            stmt = stmt.where(StockLedgerModel.material_id == material_id)
        stmt = stmt.order_by(StockLedgerModel.transaction_date.desc()).limit(limit)
        
        res = await session.execute(stmt)
        entries = res.scalars().all()
        return [StockLedgerResponse.model_validate(e) for e in entries]

@router.get("/realtime", response_model=List[RealtimeStockResponse])
async def get_realtime_stock(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id)
):
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(MaterialModel).where(MaterialModel.tenant_id == tenant_id, MaterialModel.is_active == True)
        res = await session.execute(stmt)
        materials = res.scalars().all()
        
        results = []
        for m in materials:
            results.append(RealtimeStockResponse(
                material_id=m.id,
                material_code=m.code,
                material_name=m.name,
                current_stock=float(m.current_stock),
                reserved_stock=float(m.reserved_stock),
                available_stock=float(m.current_stock - m.reserved_stock)
            ))
        return results
