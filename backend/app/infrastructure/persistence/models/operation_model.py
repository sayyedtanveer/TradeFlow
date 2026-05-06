from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.infrastructure.persistence.database import Base


class OperationModel(Base):
    __tablename__ = "operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workstation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workstations.id"), nullable=False, index=True
    )
    setup_time: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0) # In minutes
    run_time: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)   # In minutes per unit
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workstation: Mapped["WorkstationModel"] = relationship(
        "WorkstationModel", back_populates="operations", lazy="joined"
    )
    bom_operations: Mapped[list["BOMOperationModel"]] = relationship(
        "BOMOperationModel", back_populates="operation", lazy="select"
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
