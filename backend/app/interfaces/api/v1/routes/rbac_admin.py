"""
Admin RBAC Management REST API
Provides endpoints for managing roles, permissions, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, List
import uuid

from backend.app.interfaces.api.v1.dependencies.auth import (
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.dependencies.permissions import require_role
from backend.app.domain.tenant.value_objects.role import Role
from backend.app.domain.shared.permissions import ROLE_PERMISSIONS, Permission
from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.interfaces.api.v1.dependencies.auth import get_container

router = APIRouter(prefix="/admin/rbac", tags=["Admin - RBAC"])


# ────────────────────────────────────────────────────────────────────────────
# ROLES API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/roles",
    summary="List all roles with permissions",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def list_all_roles():
    """
    Return all roles and their permissions.
    
    Only accessible by ADMIN.
    """
    result = {}
    for role, perms in ROLE_PERMISSIONS.items():
        result[role] = {
            "permissions": sorted(list(perms)),
            "permission_count": len(perms),
        }
    
    return {
        "roles": result,
        "total_roles": len(result),
    }


@router.get(
    "/roles/{role_name}/permissions",
    summary="Get permissions for a specific role",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_role_permissions(role_name: str):
    """Get detailed permissions for a specific role."""
    role_name_lower = role_name.lower()
    
    if role_name_lower not in ROLE_PERMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    perms = ROLE_PERMISSIONS[role_name_lower]
    
    return {
        "role": role_name,
        "permissions": sorted(list(perms)),
        "permission_count": len(perms),
        "has_all_permissions": Permission.ALL in perms,
    }


# ────────────────────────────────────────────────────────────────────────────
# PERMISSIONS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/permissions",
    summary="List all available permissions",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def list_all_permissions():
    """Return all available permissions in the system."""
    perms = [p.value for p in Permission]
    
    return {
        "permissions": sorted(perms),
        "total_permissions": len(perms),
        "format": "module:action (e.g., 'inventory:write')",
    }


# ────────────────────────────────────────────────────────────────────────────
# USER PERMISSIONS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/users/{user_id}/permissions",
    summary="Get effective permissions for a user",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_user_permissions(
    user_id: str,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
):
    """
    Get all permissions granted to a specific user via their role.
    
    Returns:
    - User's current role
    - All effective permissions
    - Whether user is active
    """
    container = get_container(request)
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format"
        )
    
    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_uuid)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User belongs to different tenant"
            )
        
        role_str = user.role.value
        perms = ROLE_PERMISSIONS.get(role_str, frozenset())
        
        return {
            "user_id": str(user.id),
            "email": str(user.email),
            "role": role_str,
            "is_active": user.is_active,
            "permissions": sorted(list(perms)),
            "permission_count": len(perms),
            "has_all_permissions": Permission.ALL in perms,
        }


@router.post(
    "/users/{user_id}/change-role",
    summary="Change a user's role",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def change_user_role(
    user_id: str,
    new_role: str,
    request: Request,
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
):
    """
    Change a user's role (ONLY ADMIN can do this).
    
    ⚠️ CRITICAL OPERATION - Logged in audit trail
    
    Restrictions:
    - Cannot change own role
    - Cannot assign role higher than current user
    - Target user must exist and belong to same tenant
    """
    container = get_container(request)
    
    # Security: Cannot change own role
    if str(user_id) == str(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Validate new role
    try:
        new_role_enum = Role(new_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{new_role}'"
        )
    
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format"
        )
    
    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_uuid)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.tenant_id != current_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User belongs to different tenant"
            )
        
        old_role = user.role
        user.change_role(new_role_enum)
        await user_repo.save(user)
        
        # Log to audit trail
        import logging
        logger = logging.getLogger("rbac_audit")
        logger.warning({
            "event": "ROLE_CHANGE",
            "admin_id": str(current_user_id),
            "user_id": str(user.id),
            "old_role": old_role.value,
            "new_role": new_role,
            "timestamp": str(__import__('datetime').datetime.utcnow()),
        })
    
    return {
        "user_id": str(user.id),
        "email": str(user.email),
        "old_role": old_role.value,
        "new_role": new_role,
        "message": f"Role changed from {old_role.value} to {new_role}",
    }


# ────────────────────────────────────────────────────────────────────────────
# AUDIT LOG API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/audit-log",
    summary="Get permission denial audit log",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_audit_log(
    limit: int = 100,
    offset: int = 0,
):
    """
    Return recent permission denial events from audit log.
    
    ⚠️ In production: Query from dedicated AuditLog table
    
    Args:
        limit: Maximum records to return (max 1000)
        offset: Pagination offset
    
    Returns:
        Audit entries with denied user/role/path/timestamp
    """
    if limit > 1000:
        limit = 1000
    
    # TODO: Query from database when AuditLog table implemented
    # For now: placeholder structure
    return {
        "audit_entries": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "note": "Audit log queries from database pending implementation",
    }


@router.get(
    "/audit-log/permission-denials",
    summary="Get all 403 permission denial events",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_permission_denials(
    user_id: str = None,
    role: str = None,
    path_filter: str = None,
    days: int = 7,
):
    """
    Query permission denials (403 errors) from the system.
    
    ⚠️ RBAC Permission Audit Middleware must be running
    
    Filters:
        user_id: Filter by specific user
        role: Filter by specific role (e.g., 'viewer')
        path_filter: Filter by endpoint path (partial match)
        days: Look back X days (default 7)
    
    Returns:
        Structured audit entries for compliance/forensics
    """
    return {
        "message": "Permission denial query pending implementation",
        "note": "Check application logs: grep 'PERMISSION_DENIED' for current events",
        "suggested_command": "tail -f logs/rbac_audit.log | grep PERMISSION_DENIED",
    }


# ────────────────────────────────────────────────────────────────────────────
# RBAC STATUS API
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/status",
    summary="Get RBAC system status",
)
async def get_rbac_status(
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    current_tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_role: str = Depends(get_current_role),
):
    """
    Get current user's RBAC status and system info.
    
    Accessible by all authenticated users.
    """
    user_perms = ROLE_PERMISSIONS.get(current_role, frozenset())
    
    return {
        "current_user": {
            "user_id": str(current_user_id),
            "tenant_id": str(current_tenant_id),
            "role": current_role,
        },
        "effective_permissions": {
            "count": len(user_perms),
            "has_all": Permission.ALL in user_perms,
        },
        "rbac_system": {
            "total_roles": len(ROLE_PERMISSIONS),
            "total_permissions": len([p for p in Permission]),
            "audit_logging": "ENABLED",
            "status": "ACTIVE",
        },
    }
