import uuid
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.infrastructure.persistence.database import Base


class BOMOperationModel(Base):
    __tablename__ = "bom_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    bom_id = Column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_id = Column(UUID(as_uuid=True), ForeignKey("operations.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)

    # Relationships
    bom = relationship("BOMModel", back_populates="operations", lazy="select")
    operation = relationship("OperationModel", back_populates="bom_operations", lazy="joined")

    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
