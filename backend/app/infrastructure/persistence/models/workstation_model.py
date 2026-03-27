from sqlalchemy import Column, String, Numeric, Boolean, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

from backend.app.infrastructure.persistence.database import Base


class WorkstationModel(Base):
    __tablename__ = "workstations"

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_workstation_tenant_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    capacity_hours_per_day = Column(Numeric(10, 2), nullable=False, default=8.0)
    hourly_rate = Column(Numeric(14, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)

    operations = relationship("OperationModel", back_populates="workstation", lazy="select")

    # Audit fields
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
