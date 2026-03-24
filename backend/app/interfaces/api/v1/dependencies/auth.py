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
    set_request_context(
        user_id=payload.get("sub"),
        tenant_id=payload.get("tid"),
    )
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
