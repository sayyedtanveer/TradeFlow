from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_payload


async def require_client_role(
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    if str(payload.get("role", "")).lower() != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal access requires a client account",
        )
    return payload


async def require_client_id(
    payload: dict = Depends(require_client_role),
) -> uuid.UUID:
    cid = payload.get("cid")
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal: user must be linked to a client",
        )
    try:
        return uuid.UUID(str(cid))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client id in token",
        ) from exc
