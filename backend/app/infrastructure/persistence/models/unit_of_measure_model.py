from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint

from backend.app.infrastructure.persistence.database import Base


class UnitOfMeasureModel(Base):
    __tablename__ = "units_of_measure"

    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    precision = Column(Integer, default=2, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_uom_tenant_code"),
    )
