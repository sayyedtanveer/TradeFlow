"""SQLAlchemy models for pick lists in the warehouse fulfilment workflow.

Pick lists are generated when a warehouse user accepts an order (ASSIGNED → ACCEPTED).
They contain the product details and storage locations needed for physical picking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index, UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class PickListModel(Base):
    """SQLAlchemy model for the pick_lists table."""

    __tablename__ = "pick_lists"

    __table_args__ = (
        UniqueConstraint("tenant_id", "order_id", name="uq_pick_list_tenant_order"),
        Index("ix_pick_lists_tenant_id", "tenant_id"),
        Index("ix_pick_lists_order_id", "order_id"),
        Index("ix_pick_lists_warehouse_id", "warehouse_id"),
        Index("ix_pick_lists_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Updated timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    lines: Mapped[List["PickListLineModel"]] = relationship(
        "PickListLineModel",
        back_populates="pick_list",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PickListModel id={self.id} order_id={self.order_id} status={self.status}>"


class PickListLineModel(Base):
    """SQLAlchemy model for the pick_list_lines table."""

    __tablename__ = "pick_list_lines"

    __table_args__ = (
        Index("ix_pick_list_lines_pick_list_id", "pick_list_id"),
        Index("ix_pick_list_lines_product_id", "product_id"),
        Index("ix_pick_list_lines_order_line_id", "order_line_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pick_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pick_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_order_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_location: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    is_picked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    picked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    pick_list: Mapped["PickListModel"] = relationship(
        "PickListModel", back_populates="lines", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<PickListLineModel id={self.id} "
            f"product={self.product_name} qty={self.quantity}>"
        )
