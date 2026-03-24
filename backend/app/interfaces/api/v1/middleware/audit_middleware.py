from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/uploads"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Post-response middleware — writes an audit record for every
    state-changing API call (POST/PUT/PATCH/DELETE).

    Reads tenant_id, user_id, correlation_id from ContextVars
    (already populated by RequestLoggingMiddleware + TenantMiddleware).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Only audit write operations on non-system paths
        if (
            request.method in _WRITE_METHODS
            and not any(request.url.path.startswith(p) for p in _SKIP_PATHS)
        ):
            try:
                audit_service = request.app.state.container.audit_service
                await audit_service.log_action(
                    action=f"HTTP_{request.method}",
                    entity_type="api_request",
                    extra={
                        "path": request.url.path,
                        "status_code": response.status_code,
                    },
                )
            except Exception as exc:
                logger.error(
                    "AuditMiddleware failed to log",
                    extra={"error": str(exc)},
                )

        return response
