@echo off
REM Manual PostgreSQL Schema Update using psql
REM This connects to PostgreSQL and runs the schema updates

setlocal enabledelayedexpansion

REM Get database connection details from environment or hardcode
set DB_HOST=localhost
set DB_PORT=5432
set DB_USER=medtrack_user
set DB_NAME=medtrack_db
set DB_PASSWORD=your_password_here

echo.
echo ============================================
echo PostgreSQL Manual Schema Update
echo ============================================
echo.
echo Database: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo User: %DB_USER%
echo.

REM Run the SQL script
echo Executing schema update SQL...
echo.

psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f schema_update_manual.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo SUCCESS! Schema updated successfully
    echo ============================================
) else (
    echo.
    echo ============================================
    echo ERROR! Schema update failed
    echo ============================================
    pause
    exit /b 1
)

echo.
pause
