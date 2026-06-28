# PowerShell Script to Apply Operation Master Schema Changes
# Executes the SQL script against PostgreSQL database

param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$DbHost = "localhost",
    [string]$DbPort = "5432",
    [string]$DbName = "medtrack",
    [string]$DbUser = "postgres",
    [string]$DbPassword = "postgres"
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Operation Master Schema Update" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# If DATABASE_URL is provided, parse it
if ($DatabaseUrl) {
    Write-Host "Using DATABASE_URL connection string..." -ForegroundColor Yellow
    # Parse postgresql://user:password@host:port/database format
    $Uri = [System.Uri]$DatabaseUrl
    $DbUser = $Uri.UserInfo.Split(':')[0]
    $DbPassword = $Uri.UserInfo.Split(':')[1]
    $DbHost = $Uri.Host
    $DbPort = if ($Uri.Port) { $Uri.Port } else { 5432 }
    $DbName = $Uri.AbsolutePath.Trim('/')
}

$SqlFile = "db_scripts/add_operation_master_schema.sql"

if (-not (Test-Path $SqlFile)) {
    Write-Host "❌ SQL file not found: $SqlFile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Database Configuration:" -ForegroundColor Cyan
Write-Host "  Host: $DbHost"
Write-Host "  Port: $DbPort"
Write-Host "  Database: $DbName"
Write-Host "  User: $DbUser"
Write-Host ""

# Try to connect and execute
try {
    Write-Host "Executing SQL script..." -ForegroundColor Yellow
    
    # Build psql connection string
    $ConnectionString = "host=$DbHost port=$DbPort dbname=$DbName user=$DbUser password=$DbPassword"
    
    # Execute SQL file
    $env:PGPASSWORD = $DbPassword
    
    # Use psql to execute the file
    psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $SqlFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "================================================" -ForegroundColor Green
        Write-Host "✅ Schema Update SUCCESSFUL" -ForegroundColor Green
        Write-Host "================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Run: python backend/db_scripts/seed_operations.py" -ForegroundColor White
        Write-Host "2. Verify operations in database" -ForegroundColor White
        Write-Host "3. Test Operation Master API" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "❌ SQL execution failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
