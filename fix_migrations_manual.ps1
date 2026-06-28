# Manual Migration Fix Script
# This script resolves the duplicate table issue and adds missing schema columns

Write-Host "Starting manual migration fix..." -ForegroundColor Cyan

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .venv\Scripts\Activate.ps1

# Step 1: Check current migration status
Write-Host "Checking current migration status..." -ForegroundColor Yellow
alembic current
Write-Host ""

# Step 2: Upgrade to latest applied migration first
Write-Host "Upgrading to current head..." -ForegroundColor Yellow
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "Attempting to stamp phase5 and retry..." -ForegroundColor Yellow
    alembic stamp phase5_mrp_suggestions
    alembic upgrade head
}
Write-Host ""

# Step 3: Check migration status
Write-Host "Current migration status:" -ForegroundColor Yellow
alembic current
Write-Host ""

# Step 4: Generate autogenerate migration for schema changes
Write-Host "Generating autogenerate migration for schema updates..." -ForegroundColor Yellow
alembic revision --autogenerate -m "sync_schema_add_length_uom_and_other_changes"
if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully generated autogenerate migration." -ForegroundColor Green
} else {
    Write-Host "Error: Could not generate migration. Check ORM models." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Apply the new migration
Write-Host "Applying new schema migration..." -ForegroundColor Yellow
alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully applied migration!" -ForegroundColor Green
} else {
    Write-Host "Error: Migration failed." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Verify final state
Write-Host "Final migration status:" -ForegroundColor Yellow
alembic current
Write-Host ""

Write-Host "Migration fix complete!" -ForegroundColor Green
