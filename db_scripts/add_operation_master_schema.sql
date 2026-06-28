-- Manual SQL Schema Update for Operation Master
-- This script adds all necessary columns to the operations table for the Operation Master feature
-- Safe to run multiple times (checks for column existence)

-- 1. Add operation_code (business code like 10, 20, 30)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='operation_code'
    ) THEN 
        ALTER TABLE operations ADD COLUMN operation_code VARCHAR(10);
    END IF; 
END $$;

-- 2. Add operation_type (CUTTING, MACHINING, ASSEMBLY, etc.)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='operation_type'
    ) THEN 
        ALTER TABLE operations ADD COLUMN operation_type VARCHAR(32) DEFAULT 'other';
    END IF; 
END $$;

-- 3. Add default_sequence (ordering in routing)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='default_sequence'
    ) THEN 
        ALTER TABLE operations ADD COLUMN default_sequence INTEGER DEFAULT 10;
    END IF; 
END $$;

-- 4. Add estimated_time_minutes (for planning)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='estimated_time_minutes'
    ) THEN 
        ALTER TABLE operations ADD COLUMN estimated_time_minutes NUMERIC(10, 2);
    END IF; 
END $$;

-- 5. Add qc_required flag
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='qc_required'
    ) THEN 
        ALTER TABLE operations ADD COLUMN qc_required BOOLEAN DEFAULT FALSE;
    END IF; 
END $$;

-- 6. Add color for UI
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='color'
    ) THEN 
        ALTER TABLE operations ADD COLUMN color VARCHAR(20);
    END IF; 
END $$;

-- 7. Add icon_code for UI
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='icon_code'
    ) THEN 
        ALTER TABLE operations ADD COLUMN icon_code VARCHAR(50);
    END IF; 
END $$;

-- 8. Add created_by for audit trail
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='created_by'
    ) THEN 
        ALTER TABLE operations ADD COLUMN created_by UUID;
    END IF; 
END $$;

-- 9. Add is_deleted for soft deletes
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='is_deleted'
    ) THEN 
        ALTER TABLE operations ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
    END IF; 
END $$;

-- 10. Add deleted_at for soft delete tracking
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='deleted_at'
    ) THEN 
        ALTER TABLE operations ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF; 
END $$;

-- 11. Make workstation_id nullable (was previously NOT NULL)
DO $$ 
BEGIN 
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='operations' AND column_name='workstation_id' AND is_nullable='NO'
    ) THEN 
        ALTER TABLE operations ALTER COLUMN workstation_id DROP NOT NULL;
    END IF; 
END $$;

-- 12. Create unique constraint on (tenant_id, operation_code)
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage 
        WHERE table_name='operations' AND constraint_name='uq_operations_tenant_code'
    ) THEN 
        ALTER TABLE operations ADD CONSTRAINT uq_operations_tenant_code UNIQUE (tenant_id, operation_code);
    END IF; 
END $$;

-- 13. Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_operations_tenant_active 
ON operations(tenant_id, is_deleted) 
WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS ix_operations_tenant_sequence 
ON operations(tenant_id, default_sequence) 
WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS ix_operations_code 
ON operations(operation_code) 
WHERE is_deleted = false;

-- Verification: Show the operations table structure
\d operations
