from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status

from backend.app.interfaces.api.v1.dependencies.auth import get_current_user_payload


async def require_supplier_id(
    payload: dict = Depends(get_current_user_payload),
) -> uuid.UUID:
    sid = payload.get("sid")
    if not sid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier portal: user must be linked to a supplier",
        )
    try:
        return uuid.UUID(sid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid supplier id") from e
