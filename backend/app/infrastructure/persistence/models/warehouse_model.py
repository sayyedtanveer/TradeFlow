"""SQLAlchemy models for the Warehouse bounded context."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Index, UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class WarehouseModel(Base):
    """SQLAlchemy model for the warehouses table."""

    __tablename__ = "warehouses"

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_warehouse_tenant_name"),
        Index("ix_warehouses_tenant_id", "tenant_id"),
        Index("ix_warehouses_is_deleted", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Address fields (flattened from Address value object)
    address_street: Mapped[str] = mapped_column(String(255), nullable=False)
    address_city: Mapped[str] = mapped_column(String(100), nullable=False)
    address_region: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    address_postal_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    address_country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Contact info
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
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

    def __repr__(self) -> str:
        return f"<WarehouseModel id={self.id} name={self.name}>"


class WarehouseUserAssignmentModel(Base):
    """SQLAlchemy model for the warehouse_user_assignments table."""

    __tablename__ = "warehouse_user_assignments"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "user_id", name="uq_warehouse_user_assignment_tenant_user"
        ),
        Index("ix_warehouse_user_assignments_tenant_id", "tenant_id"),
        Index("ix_warehouse_user_assignments_warehouse_id", "warehouse_id"),
        Index("ix_warehouse_user_assignments_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
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

    def __repr__(self) -> str:
        return f"<WarehouseUserAssignmentModel id={self.id} user_id={self.user_id} warehouse_id={self.warehouse_id}>"


class WarehouseProductThresholdModel(Base):
    """SQLAlchemy model for the warehouse_product_thresholds table."""

    __tablename__ = "warehouse_product_thresholds"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "warehouse_id",
            "product_id",
            name="uq_warehouse_product_threshold_tenant_wh_product",
        ),
        Index("ix_warehouse_product_thresholds_tenant_id", "tenant_id"),
        Index("ix_warehouse_product_thresholds_warehouse_id", "warehouse_id"),
        Index("ix_warehouse_product_thresholds_product_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
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

    def __repr__(self) -> str:
        return f"<WarehouseProductThresholdModel id={self.id} warehouse_id={self.warehouse_id} product_id={self.product_id}>"
