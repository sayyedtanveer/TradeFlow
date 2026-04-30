"""User management API endpoints."""

from __future__ import annotations

import secrets
import string
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.models.supplier_model import SupplierModel
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_container,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_role
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.interfaces.api.v1.schemas.auth_schemas import (
    UserInMeResponse,
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/users", tags=["Users"])


class UserCreateRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool = True
    supplier_id: Optional[str] = None  # Link to supplier if creating supplier portal user


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    supplier_id: Optional[str] = None


class UserCreateResponse(BaseModel):
    """Response when creating a user - includes temporary password."""
    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    tenant_id: str
    is_active: bool
    supplier_id: Optional[str] = None
    client_id: Optional[str] = None
    temporary_password: str = Field(
        description="Temporary password for first login. User must change this after login."
    )


def _generate_temporary_password(length: int = 12) -> str:
    """Generate a secure random temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.get(
    "",
    response_model=List[UserInMeResponse],
    dependencies=[Depends(require_role(Role.ADMIN))],
    summary="List all users in tenant",
)
async def list_users(
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """Get all users for the current tenant with optional filtering."""
    container = get_container(request)
    async with container.session_factory() as session:
        stmt = select(UserModel).where(
            UserModel.tenant_id == tenant_id,
            UserModel.is_deleted.is_(False),
        )

        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                (UserModel.email.ilike(search_pattern))
                | (UserModel.first_name.ilike(search_pattern))
                | (UserModel.last_name.ilike(search_pattern))
            )

        if role:
            stmt = stmt.where(UserModel.role == role)

        if is_active is not None:
            stmt = stmt.where(UserModel.is_active == is_active)

        result = await session.execute(stmt)
        users = result.scalars().all()

        # Convert to response model with explicit field mapping
        user_responses = [
            UserInMeResponse(
                id=str(u.id),
                email=u.email,
                first_name=u.first_name,
                last_name=u.last_name,
                role=u.role,
                tenant_id=str(u.tenant_id),
                is_active=u.is_active,
                supplier_id=str(u.supplier_id) if u.supplier_id else None,
                client_id=str(u.client_id) if u.client_id else None,
            )
            for u in users
        ]

    return user_responses


@router.get(
    "/{user_id}",
    response_model=UserInMeResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
    summary="Get user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Get a specific user in the current tenant."""
    container = get_container(request)
    async with container.session_factory() as session:
        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserInMeResponse.model_validate(user)


@router.post(
    "",
    response_model=UserCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.ADMIN))],
    summary="Create a new user",
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Create a new user in the current tenant with a temporary password."""
    container = get_container(request)

    async with container.session_factory() as session:
        # Check if email already exists
        result = await session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant_id,
                UserModel.email == body.email,
                UserModel.is_deleted.is_(False),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already exists")

        # CRITICAL: If supplier_id provided, validate it belongs to current tenant
        supplier_id_value = None
        if body.supplier_id:
            try:
                supplier_uuid = uuid.UUID(body.supplier_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid supplier_id format")
            
            supplier = await session.get(SupplierModel, supplier_uuid)
            if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
                raise HTTPException(status_code=404, detail="Supplier not found")
            supplier_id_value = supplier_uuid

        # Generate secure temporary password
        temporary_password = _generate_temporary_password()
        
        # Create user with hashed temporary password
        user = UserModel(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            role=body.role.lower(),
            is_active=body.is_active,
            hashed_password=container.password_hasher.hash(temporary_password),
            supplier_id=supplier_id_value,  # Set supplier_id if provided
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Return response with temporary password (only shown at creation time)
    return UserCreateResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=str(user.tenant_id),
        is_active=user.is_active,
        supplier_id=str(user.supplier_id) if user.supplier_id else None,
        client_id=str(user.client_id) if user.client_id else None,
        temporary_password=temporary_password,
    )


@router.put(
    "/{user_id}",
    response_model=UserInMeResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
    summary="Update user",
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """Update a user in the current tenant."""
    container = get_container(request)

    async with container.session_factory() as session:
        result = await session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.tenant_id == tenant_id,
                UserModel.is_deleted.is_(False),
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # CRITICAL: If supplier_id provided, validate it belongs to current tenant
        if body.supplier_id is not None:
            try:
                supplier_uuid = uuid.UUID(body.supplier_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid supplier_id format")
            
            supplier = await session.get(SupplierModel, supplier_uuid)
            if not supplier or supplier.tenant_id != tenant_id or supplier.is_deleted:
                raise HTTPException(status_code=404, detail="Supplier not found")
            user.supplier_id = supplier_uuid
        elif "supplier_id" in body.model_fields_set:
            user.supplier_id = None
        
        # Update other fields (normalize role to lowercase)
        data = body.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key == "supplier_id":
                continue  # Already handled above
            if key == "role" and isinstance(value, str):
                value = value.lower()
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)

    return UserInMeResponse.model_validate(user)
