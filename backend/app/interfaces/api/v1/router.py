from __future__ import annotations

from fastapi import APIRouter

from backend.app.interfaces.api.v1.routes.auth import router as auth_router
from backend.app.interfaces.api.v1.routes.tenants import router as tenants_router
from backend.app.interfaces.api.v1.routes.files import router as files_router
from backend.app.interfaces.api.v1.routes.inventory import router as inventory_router
from backend.app.interfaces.api.v1.routes.master_data import router as master_data_router
from backend.app.interfaces.api.v1.routes.batch_and_serial import router as batch_and_serial_router
from backend.app.interfaces.api.v1.routes.products import router as products_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(master_data_router)
api_v1_router.include_router(batch_and_serial_router)
api_v1_router.include_router(products_router)
