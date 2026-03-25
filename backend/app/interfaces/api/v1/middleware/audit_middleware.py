from __future__ import annotations

import re
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/uploads"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Maps URL pattern → (entity_type, group_index_for_entity_id)
# Each tuple: (regex, entity_type, id_group_index or None)
_ENTITY_PATTERNS = [
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/activate"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/copy"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/validate"), "bom", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})/operations"), "bom_operation", 1),
    (re.compile(r"^/api/v\d+/boms/([0-9a-f-]{36})"), "bom", 1),
    (re.compile(r"^/api/v\d+/products/([0-9a-f-]{36})/boms"), "bom", None),
    (re.compile(r"^/api/v\d+/products/templates/([0-9a-f-]{36})/variants"), "item_variant", None),
    (re.compile(r"^/api/v\d+/products/templates/([0-9a-f-]{36})"), "item_template", 1),
    (re.compile(r"^/api/v\d+/products/variants/([0-9a-f-]{36})"), "item_variant", 1),
    (re.compile(r"^/api/v\d+/operations/([0-9a-f-]{36})"), "operation", 1),
    (re.compile(r"^/api/v\d+/operations"), "operation", None),
    (re.compile(r"^/api/v\d+/workstations/([0-9a-f-]{36})"), "workstation", 1),
    (re.compile(r"^/api/v\d+/workstations"), "workstation", None),
]

_ACTION_MAP = {
    "POST": "CREATE",
    "PUT": "UPDATE",
    "PATCH": "PATCH",
    "DELETE": "DELETE",
}


def _resolve_entity(path: str) -> tuple[str | None, str | None]:
    """Returns (entity_type, entity_id) by matching path against known patterns."""
    for pattern, entity_type, id_group in _ENTITY_PATTERNS:
        m = pattern.search(path)
        if m:
            entity_id = m.group(id_group) if id_group and id_group <= len(m.groups()) else None
            return entity_type, entity_id
    return "api_request", None


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Post-response middleware — writes a structured audit record for every
    state-changing API call (POST/PUT/PATCH/DELETE).

    entity_type and entity_id are resolved from the URL path pattern.
    tenant_id, user_id, correlation_id are read from request.state (set by other middlewares).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path

        if (
            request.method in _WRITE_METHODS
            and not any(path.startswith(p) for p in _SKIP_PATHS)
        ):
            try:
                entity_type, entity_id = _resolve_entity(path)
                action = _ACTION_MAP.get(request.method, request.method)

                # Attempt to get tenant_id/user_id from request state (set by TenantMiddleware/auth)
                tenant_id = getattr(request.state, "tenant_id", None)
                user_id = getattr(request.state, "user_id", None)
                correlation_id = getattr(request.state, "correlation_id", None)

                audit_service = request.app.state.container.audit_service
                await audit_service.log_action(
                    action=action,
                    entity_type=entity_type,
                    entity_id=uuid.UUID(entity_id) if entity_id else None,
                    extra={
                        "path": path,
                        "method": request.method,
                        "status_code": response.status_code,
                    },
                )
            except Exception as exc:
                logger.error(
                    "AuditMiddleware failed to log",
                    extra={"error": str(exc)},
                )

        return response
