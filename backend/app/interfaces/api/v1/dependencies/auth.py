from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.domain.tenant.value_objects.role import Role
from backend.app.infrastructure.context.request_context import set_request_context

security = HTTPBearer(auto_error=False)


def get_container(request: Request):
    return request.app.state.container


async def get_current_user_payload(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Extract and validate JWT; return decoded payload dict."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    container = get_container(request)
    try:
        payload = container.jwt_handler.decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update context vars with authenticated user info
    user_id = payload.get("sub")
    tenant_id = payload.get("tid")
    user_role = payload.get("role", "viewer")
    
    # Populate context vars used across async tasks and logging
    set_request_context(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    # Inject easily accessible attributes into request.state for handlers/middleware
    # Keep `request.scope` untouched for compatibility; prefer `request.state` for app logic.
    try:
        # Basic user object (minimal, safe to include)
        request.state.user = {"id": user_id, "role": user_role}
        request.state.tenant_id = tenant_id
        request.state.role = user_role
        # optional supplier/client ids added by login handler as extra claims
        request.state.supplier_id = payload.get("sid")
        request.state.client_id = payload.get("cid")
    except Exception:
        # If request doesn't support state (very unlikely), silently ignore to avoid breaking auth
        pass

    # Backwards-compat: keep lightweight values on scope for middleware that read them
    request.scope["user_id"] = user_id
    request.scope["tenant_id"] = tenant_id
    request.scope["user_role"] = user_role

    return payload


async def get_current_user_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    return uuid.UUID(payload["sub"])


async def get_current_tenant_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    return uuid.UUID(payload["tid"])


async def get_current_role(
    payload: dict = Depends(get_current_user_payload),
) -> str:
    return payload.get("role", "viewer")
