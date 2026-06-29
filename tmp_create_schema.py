import os
import sys
import asyncio

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
os.environ['DATABASE_SYNC_URL'] = 'postgresql://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from backend.app.infrastructure.persistence.database import Base, create_engine

import backend.app.infrastructure.persistence.models.tenant_model  # noqa: F401
import backend.app.infrastructure.persistence.models.user_model  # noqa: F401
import backend.app.infrastructure.persistence.models.audit_log_model  # noqa: F401
import backend.app.infrastructure.persistence.models.material_model  # noqa: F401
import backend.app.infrastructure.persistence.models.inventory_transaction_model  # noqa: F401
import backend.app.infrastructure.persistence.models.material_category_model  # noqa: F401
import backend.app.infrastructure.persistence.models.unit_of_measure_model  # noqa: F401
import backend.app.infrastructure.persistence.models.uom_conversion_model  # noqa: F401
import backend.app.infrastructure.persistence.models.location_model  # noqa: F401
import backend.app.infrastructure.persistence.models.batch_model  # noqa: F401
import backend.app.infrastructure.persistence.models.serial_number_model  # noqa: F401
import backend.app.infrastructure.persistence.models.item_template_model  # noqa: F401
import backend.app.infrastructure.persistence.models.item_variant_model  # noqa: F401
import backend.app.infrastructure.persistence.models.item_code_sequence_model  # noqa: F401
import backend.app.infrastructure.persistence.models.bom_model  # noqa: F401
import backend.app.infrastructure.persistence.models.bom_operation_model  # noqa: F401
import backend.app.infrastructure.persistence.models.work_order_model  # noqa: F401
import backend.app.infrastructure.persistence.models.sales_models  # noqa: F401
import backend.app.infrastructure.persistence.models.quality_model  # noqa: F401
import backend.app.infrastructure.persistence.models.purchase_order_model  # noqa: F401
import backend.app.infrastructure.persistence.models.grn_model  # noqa: F401
import backend.app.infrastructure.persistence.models.supplier_model  # noqa: F401
import backend.app.infrastructure.persistence.models.po_sequence_model  # noqa: F401
import backend.app.infrastructure.persistence.models.material_request_model  # noqa: F401
import backend.app.infrastructure.persistence.models.mrp_model  # noqa: F401
import backend.app.infrastructure.persistence.models.subcontract_model  # noqa: F401
import backend.app.infrastructure.persistence.models.finance_models  # noqa: F401
import backend.app.infrastructure.persistence.models.inventory_management_models  # noqa: F401
import backend.app.infrastructure.persistence.models.document_model  # noqa: F401
import backend.app.infrastructure.persistence.models.material_onboarding_model  # noqa: F401
import backend.app.infrastructure.persistence.models.warehouse_model  # noqa: F401
import backend.app.infrastructure.logging.models  # noqa: F401

async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print('created all tables')

asyncio.run(main())
