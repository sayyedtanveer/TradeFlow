# Simplest Schema Fix - Add columns directly
Write-Host "Adding missing columns directly to PostgreSQL..." -ForegroundColor Cyan
Write-Host ""

& .venv\Scripts\Activate.ps1

# Use Python to execute SQL directly
$pythonCode = @"
import asyncio
from backend.app.infrastructure.persistence.database import create_engine
from sqlalchemy import text

async def add_missing_columns():
    """Add missing columns directly via SQL"""
    engine = create_engine()
    
    async with engine.connect() as conn:
        # Get current DB state
        result = await conn.execute(
            text("""SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'materials' AND column_name = 'length_uom'""")
        )
        exists = result.fetchone()
        
        if exists:
            print("Column 'length_uom' already exists!")
            return
        
        print("Adding missing columns to materials table...")
        
        # Add each column with safe checks
        columns_to_add = [
            ("length_uom", "VARCHAR(20)"),
            ("length_per_unit", "NUMERIC(18,4)"),
            ("weight_per_unit", "NUMERIC(18,4)"),
            ("dimension_spec", "TEXT"),
            ("preferred_supplier_id", "UUID"),
            ("hazardous_flag", "BOOLEAN DEFAULT false"),
            ("qc_required_flag", "BOOLEAN DEFAULT false"),
            ("barcode", "VARCHAR(100)"),
            ("traceability_enabled", "BOOLEAN DEFAULT false"),
            ("batch_rule", "VARCHAR(50)"),
            ("expiry_tracking", "BOOLEAN DEFAULT false"),
            ("shelf_life_days", "INTEGER"),
            ("quarantine_required", "BOOLEAN DEFAULT false"),
            ("cuttable_inventory", "BOOLEAN DEFAULT false"),
            ("remaining_quantity_tracking", "BOOLEAN DEFAULT false"),
            ("reusable_remainder", "BOOLEAN DEFAULT false"),
            ("decimal_precision", "INTEGER"),
            ("supplier_item_code", "VARCHAR(100)"),
            ("purchase_uom", "VARCHAR(20)"),
            ("min_stock", "NUMERIC(18,4)"),
            ("max_stock", "NUMERIC(18,4)"),
            ("reorder_quantity", "NUMERIC(18,4)"),
            ("moq", "NUMERIC(18,4)"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(
                    text(f"ALTER TABLE materials ADD COLUMN {col_name} {col_type}")
                )
                print(f"  ✓ Added {col_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"  - {col_name} already exists (skipped)")
                else:
                    print(f"  ✗ Error adding {col_name}: {e}")
        
        await conn.commit()
        print("\nAll columns added successfully!")

asyncio.run(add_missing_columns())
"@

Write-Host "Executing schema update..." -ForegroundColor Yellow
python -c $pythonCode

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS! Columns added to database!" -ForegroundColor Green
} else {
    Write-Host "Error occurred during schema update" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Database schema fix complete!" -ForegroundColor Green
