from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Numeric, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.infrastructure.persistence.database import Base


class MaterialModel(Base):
    __tablename__ = "materials"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_material_tenant_code"),
        Index("ix_materials_tenant_id", "tenant_id"),
        Index("ix_materials_is_deleted", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)

    category_id = Column(UUID(as_uuid=True), ForeignKey("material_categories.id"), index=True, nullable=True)
    base_unit_id = Column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=True)
    
    material_type = Column(String(20), nullable=False, default="raw") # raw, finished

    # Stock fields — stored as NUMERIC for precision
    current_stock: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    reserved_stock: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    reorder_level: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)

    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    is_batch_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_serialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MaterialModel id={self.id} code={self.code}>"
