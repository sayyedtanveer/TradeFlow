"""
RBAC Permission Audit Logging Middleware.
Logs all permission denials (403 responses) to the audit trail for compliance & forensics.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.app.infrastructure.persistence.models.audit_log_model import AuditLogModel

logger = logging.getLogger("rbac_audit")


class RBACPermissionAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all permission denials (403 responses) to:
    1. Python logging (structured format for log aggregation)
    2. Database audit trail (persistent record for compliance queries)

    Captures: who tried what, when, from where, and with what role.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Log 403 responses with full context
        if response.status_code == 403:
            # Extract user context from request scope (set by auth dependency)
            user_id = request.scope.get("user_id", "unknown")
            tenant_id = request.scope.get("tenant_id", "unknown")
            user_role = request.scope.get("user_role", "unknown")

            # Extract path/method
            path = request.url.path
            method = request.method
            timestamp = datetime.now(timezone.utc)

            # Log with structured format for easy parsing
            logger.warning(
                f"PERMISSION_DENIED | "
                f"path={path} | "
                f"method={method} | "
                f"user_id={user_id} | "
                f"tenant_id={tenant_id} | "
                f"role={user_role} | "
                f"timestamp={timestamp.isoformat()}"
            )

            # Persist to database audit trail
            await self._persist_denial_to_audit_trail(
                request=request,
                user_id=user_id,
                tenant_id=tenant_id,
                user_role=user_role,
                path=path,
                method=method,
                timestamp=timestamp,
            )

        return response

    async def _persist_denial_to_audit_trail(
        self,
        request: Request,
        user_id: str,
        tenant_id: str,
        user_role: str,
        path: str,
        method: str,
        timestamp: datetime,
    ) -> None:
        """Persist permission denial to the audit_logs table.

        This ensures every 403 is queryable by Admin via the audit log API.
        Failures here must never break the original response.
        """
        try:
            container = getattr(request.app.state, "container", None)
            if container is None:
                return

            session_factory = getattr(container, "session_factory", None)
            if session_factory is None:
                return

            # Parse UUIDs safely
            parsed_tenant_id = None
            parsed_user_id = None
            try:
                if tenant_id and tenant_id != "unknown":
                    parsed_tenant_id = uuid.UUID(str(tenant_id))
            except (ValueError, TypeError):
                pass
            try:
                if user_id and user_id != "unknown":
                    parsed_user_id = uuid.UUID(str(user_id))
            except (ValueError, TypeError):
                pass

            # Get client IP
            client_ip = None
            if hasattr(request, "client") and request.client:
                client_ip = request.client.host

            record = AuditLogModel(
                id=uuid.uuid4(),
                tenant_id=parsed_tenant_id,
                user_id=parsed_user_id,
                action="PERMISSION_DENIED",
                entity_type="api_endpoint",
                entity_id=None,
                before_value=None,
                after_value=None,
                ip_address=client_ip,
                correlation_id=None,
                extra={
                    "path": path,
                    "method": method,
                    "role": user_role,
                    "denied_at": timestamp.isoformat(),
                },
                occurred_at=timestamp,
            )

            async with session_factory() as session:
                session.add(record)
                await session.commit()

        except Exception as exc:
            # Audit persistence failures must never break the main response
            logger.error(
                f"Failed to persist PERMISSION_DENIED audit record: {exc}",
                exc_info=False,
            )
