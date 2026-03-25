import uuid
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.infrastructure.persistence.database import Base


class OperationModel(Base):
    __tablename__ = "operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    workstation_id = Column(UUID(as_uuid=True), ForeignKey("workstations.id"), nullable=False, index=True)
    setup_time = Column(Numeric(10, 2), nullable=False, default=0.0) # In minutes
    run_time = Column(Numeric(10, 2), nullable=False, default=0.0)   # In minutes per unit
    description = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    workstation = relationship("WorkstationModel", back_populates="operations", lazy="joined")
    bom_operations = relationship("BOMOperationModel", back_populates="operation", lazy="select")

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
