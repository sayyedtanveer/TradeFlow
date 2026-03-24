from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.infrastructure.context.request_context import (
    clear_request_context,
    set_request_context,
)
from backend.app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Outermost middleware — runs first on request, last on response.

    Responsibilities:
    1. Generate correlation_id for the request
    2. Set request context (correlation_id, ip_address) in ContextVars
    3. Log request start and end with timing
    4. Clear context vars after response
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = str(uuid.uuid4())
        ip_address = request.client.host if request.client else "unknown"
        start = time.perf_counter()

        # Set context vars — available globally for this request
        set_request_context(
            correlation_id=correlation_id,
            ip_address=ip_address,
        )

        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "ip": ip_address,
            },
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # Inject correlation_id into response header for client-side tracing
        response.headers["X-Correlation-ID"] = correlation_id

        clear_request_context()
        return response
