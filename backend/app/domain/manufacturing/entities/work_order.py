"""Minimal WorkOrderStatus enum stub — retained for infrastructure model compatibility.

The full WorkOrder domain entity and state machine have been removed.
This stub exists only so that work_order_model.py (SQLAlchemy) can reference
the enum values until the manufacturing tables are dropped by migration.
"""
from __future__ import annotations

import enum


class WorkOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    MATERIAL_PENDING = "MATERIAL_PENDING"
    MATERIAL_RESERVED = "MATERIAL_RESERVED"
    MATERIAL_ISSUED = "MATERIAL_ISSUED"
    IN_PRODUCTION = "IN_PRODUCTION"
    QC_PENDING = "QC_PENDING"
    QC_APPROVED = "QC_APPROVED"
    QC_REJECTED = "QC_REJECTED"
    FG_RECEIVED = "FG_RECEIVED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    REWORK = "REWORK"
    REJECTED = "REJECTED"


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class InvalidStatusTransitionError(Exception):
    """Raised when a lifecycle transition is not permitted."""
    error_code = "INVALID_STATUS_TRANSITION"
