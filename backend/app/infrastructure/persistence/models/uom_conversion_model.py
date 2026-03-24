from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class UomConversionModel(Base):
    __tablename__ = "uom_conversions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    
    from_uom_id = Column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=False)
    to_uom_id = Column(UUID(as_uuid=True), ForeignKey("units_of_measure.id"), nullable=False)
    
    conversion_factor = Column(Numeric(15, 6), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "from_uom_id", "to_uom_id", name="uq_uom_conv_tenant_from_to"),
    )
