from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import get_settings
from backend.app.infrastructure.container import Container
from backend.app.infrastructure.logging.logger import get_logger
from backend.app.interfaces.api.v1.middleware.logging_middleware import RequestLoggingMiddleware
from backend.app.interfaces.api.v1.middleware.tenant_middleware import TenantMiddleware
from backend.app.interfaces.api.v1.middleware.audit_middleware import AuditMiddleware
from backend.app.interfaces.api.v1.router import api_v1_router
from backend.app.core.module_registry import module_registry

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan – startup and shutdown."""
    logger.info("Starting MedTrack ERP", extra={"version": settings.app_version})

    # Build DI container once
    container = Container.create(settings)
    app.state.container = container

    # Create upload directory
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Freeze the system map to prevent mutations and ensure dependencies are valid
    module_registry.lock()

    logger.info("Application startup complete")
    yield

    # Shutdown
    await container.db_engine.dispose()
    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-tenant Manufacturing ERP — Phase 0 Foundation",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost first) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Static file serving for uploads ──────────────
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    # ── Routers ───────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Health check ──────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": settings.app_version,
        }

    return app


app = create_application()
