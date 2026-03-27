from __future__ import annotations

import uuid
import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Numeric, Boolean, Date, DateTime,
    ForeignKey, Enum as SAEnum, Integer, Text, UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.infrastructure.persistence.database import Base


class WorkOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class WorkOrderModel(Base):
    __tablename__ = "work_orders"

    __table_args__ = (
        UniqueConstraint("tenant_id", "wo_number", name="uq_work_order_tenant_number"),
        Index("ix_work_orders_tenant_status", "tenant_id", "status"),
        Index("ix_work_orders_tenant_due", "tenant_id", "due_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wo_number = Column(String(30), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Product / BOM snapshot references (immutable after RELEASED)
    product_id = Column(UUID(as_uuid=True), ForeignKey("item_variants.id", ondelete="RESTRICT"), nullable=False)
    bom_id = Column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="RESTRICT"), nullable=False)
    sales_order_id = Column(UUID(as_uuid=True), nullable=True)

    # Quantities
    planned_quantity = Column(Numeric(15, 3), nullable=False)
    produced_quantity = Column(Numeric(15, 3), nullable=False, default=0)
    scrap_quantity = Column(Numeric(15, 3), nullable=False, default=0)

    # Lifecycle
    status = Column(SAEnum(WorkOrderStatus, name="work_order_status"), nullable=False, default=WorkOrderStatus.PLANNED)
    priority = Column(SAEnum(WorkOrderPriority, name="work_order_priority"), nullable=False, default=WorkOrderPriority.NORMAL)

    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    materials = relationship("WorkOrderMaterialModel", back_populates="work_order", cascade="all, delete-orphan")
    job_cards = relationship("JobCardModel", back_populates="work_order", cascade="all, delete-orphan", order_by="JobCardModel.sequence")
    production_records = relationship("ProductionRecordModel", back_populates="work_order", cascade="all, delete-orphan")


class WorkOrderMaterialModel(Base):
    """BOM snapshot — copied from BOM lines at WO creation. Never re-reads live BOM."""
    __tablename__ = "work_order_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=False)
    required_quantity = Column(Numeric(15, 3), nullable=False)
    issued_quantity = Column(Numeric(15, 3), nullable=False, default=0)

    work_order = relationship("WorkOrderModel", back_populates="materials")


class JobCardModel(Base):
    """Operation snapshot — copied from BOM operation list at WO creation."""
    __tablename__ = "job_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id", ondelete="RESTRICT"), nullable=False)
    sequence = Column(Integer, nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING / IN_PROGRESS / DONE
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    remarks = Column(Text, nullable=True)

    work_order = relationship("WorkOrderModel", back_populates="job_cards")


class ProductionRecordModel(Base):
    __tablename__ = "production_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    produced_quantity = Column(Numeric(15, 3), nullable=False)
    scrap_quantity = Column(Numeric(15, 3), nullable=False, default=0)
    recorded_by = Column(UUID(as_uuid=True), nullable=False)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    work_order = relationship("WorkOrderModel", back_populates="production_records")


class WONumberSequenceModel(Base):
    """One row per tenant — atomically incremented to generate WO numbers."""
    __tablename__ = "wo_number_sequences"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True)
    current_value = Column(Integer, nullable=False, default=0)
