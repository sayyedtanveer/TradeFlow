import asyncio
import os
import sys

# Add the parent directory to sys.path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import create_engine, Base

# Import all models so they are registered with Base.metadata
from backend.app.infrastructure.persistence.models import (
    user_model, tenant_model, workstation_model, operation_model,
    material_category_model, unit_of_measure_model, location_model,
    material_model, item_template_model, item_variant_model,
    bom_operation_model, bom_model, work_order_model,
    inventory_transaction_model, serial_number_model, batch_model,
    uom_conversion_model, sales_models, audit_log_model
)


async def run_migration():
    settings = get_settings()
    engine = create_engine(settings.database_url)

    print("Starting Phase 4 DB Migration...")
    
    async with engine.begin() as conn:
        print("1. Replacing global unique index on workstations.code with per-tenant constraint...")
        try:
            # 1. Drop the old global unique index
            await conn.execute(text("DROP INDEX IF EXISTS ix_workstations_code;"))
            print("   Dropped ix_workstations_code.")
            
            # 2. Add the unique constraint on (tenant_id, code)
            # Use IF NOT EXISTS equivalent by just catching the exception
            await conn.execute(text("ALTER TABLE workstations ADD CONSTRAINT uix_workstation_tenant_code UNIQUE (tenant_id, code);"))
            print("   Added uix_workstation_tenant_code.")
        except Exception as e:
            print(f"   Note: constraint might already exist or failed: {e}")

        print("2. Creating new tables (work_orders, work_order_materials, job_cards, etc.)...")
        await conn.run_sync(Base.metadata.create_all)
        print("   Tables created successfully.")
        
    await engine.dispose()
    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(run_migration())
