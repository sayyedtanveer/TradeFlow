@echo off
REM Batch script to apply Operation Master schema changes

echo.
echo ================================================
echo   Operation Master Schema Update
echo ================================================
echo.

REM Check if psql is available
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: psql command not found. Please install PostgreSQL client tools.
    exit /b 1
)

REM Default connection parameters
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=medtrack
set DB_USER=postgres
set DB_PASSWORD=postgres

REM Check for DATABASE_URL environment variable
if not "%DATABASE_URL%"=="" (
    echo Using DATABASE_URL from environment...
    REM Parse DATABASE_URL format: postgresql://user:password@host:port/database
)

echo Database: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo User: %DB_USER%
echo.
echo Applying schema changes...
echo.

REM Execute the SQL file
set PGPASSWORD=%DB_PASSWORD%
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f db_scripts\add_operation_master_schema.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================
    echo   ^[OK^] Schema Update SUCCESSFUL
    echo ================================================
    echo.
    echo Next steps:
    echo   1. Run: python backend/db_scripts/seed_operations.py
    echo   2. Verify operations in database
    echo   3. Test Operation Master API
    echo.
) else (
    echo.
    echo ================================================
    echo   ^[FAILED^] Schema Update failed
    echo ================================================
    exit /b 1
)

REM Clear password from environment
set PGPASSWORD=
