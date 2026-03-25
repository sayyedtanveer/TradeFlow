from __future__ import annotations

from fastapi import APIRouter, Depends
from backend.app.core.module_registry import module_registry
from backend.app.interfaces.api.v1.dependencies.auth import get_current_user
from backend.app.domain.user.entities.user import User

from backend.app.interfaces.api.v1.routes.auth import router as auth_router
from backend.app.interfaces.api.v1.routes.tenants import router as tenants_router
from backend.app.interfaces.api.v1.routes.files import router as files_router
from backend.app.interfaces.api.v1.routes.inventory import router as inventory_router
from backend.app.interfaces.api.v1.routes.master_data import router as master_data_router
from backend.app.interfaces.api.v1.routes.batch_and_serial import router as batch_and_serial_router
from backend.app.interfaces.api.v1.routes.products import router as products_router
from backend.app.interfaces.api.v1.routes.boms import router as boms_router
from backend.app.interfaces.api.v1.workstations import router as workstations_router
from backend.app.interfaces.api.v1.operations import router as operations_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(inventory_router)
api_v1_router.include_router(master_data_router)
api_v1_router.include_router(batch_and_serial_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(boms_router)
api_v1_router.include_router(workstations_router)
api_v1_router.include_router(operations_router)

# --- Dynamic Module Registration ---
module_registry.register(
    id="auth",
    name="IAM & Users",
    route="/users",
    dependencies=[],
    roles=["ADMIN"],
    status="active",
    icon="Users"
)

module_registry.register(
    id="inventory",
    name="Inventory",
    route="/inventory",
    dependencies=[],
    roles=["ADMIN", "MANAGER", "OPERATOR", "VIEWER"],
    status="active",
    icon="Package"
)

module_registry.register(
    id="products",
    name="Product Master",
    route="/products",
    dependencies=["inventory"],
    roles=["ADMIN", "MANAGER"],
    status="active",
    icon="PackageSearch"
)

module_registry.register(
    id="bom",
    name="Bill of Materials",
    route="/bom",
    dependencies=["products", "inventory"],
    roles=["ADMIN", "MANAGER", "OPERATOR"],
    status="active",
    icon="Layers"
)

module_registry.register(
    id="manufacturing",
    name="Manufacturing Ops",
    route="/manufacturing",
    dependencies=["bom"],
    roles=["ADMIN", "MANAGER"],
    status="active",
    icon="Factory"
)

# --- System API Map ---
@api_v1_router.get("/system-map", tags=["System"])
async def get_system_map(current_user: User = Depends(get_current_user)):
    """Returns the dynamic system floor plan tailored to the user's role."""
    return module_registry.get_system_map(user_role=current_user.role.name)
