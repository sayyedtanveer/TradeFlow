"""Persistence models package — import all models for Alembic auto-discovery."""

from backend.app.infrastructure.persistence.models.warehouse_model import (  # noqa: F401
    WarehouseModel,
    WarehouseUserAssignmentModel,
    WarehouseProductThresholdModel,
)
