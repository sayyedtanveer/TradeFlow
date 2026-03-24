from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.context.request_context import set_request_context
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant_id from the Authorization JWT or X-Tenant-ID header
    and stores it in ContextVars.

    Does NOT enforce authentication — that's the auth dependency's job.
    Only extracts and stores tenant_id for logging and context purposes.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        tenant_id: str | None = None

        # 1. Try X-Tenant-ID header (useful for machine-to-machine calls)
        tenant_id = request.headers.get("X-Tenant-ID")

        # 2. Try to decode from JWT (best-effort, no raise on failure)
        if not tenant_id:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    container = request.app.state.container
                    payload = container.jwt_handler.decode_token(token)
                    tenant_id = payload.get("tid")
                except Exception:
                    pass  # Will fail properly in auth dependency

        if tenant_id:
            set_request_context(tenant_id=tenant_id)
            logger.debug("Tenant resolved", extra={"tenant_id": tenant_id})

        return await call_next(request)
