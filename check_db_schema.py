#!/usr/bin/env python
"""Check database schema and add missing columns."""
import os
from sqlalchemy import create_engine, text

# Get DB URL from env
db_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
sync_db_url = db_url.replace('+asyncpg', '')
print(f'DB URL: {sync_db_url}')

try:
    engine = create_engine(sync_db_url)
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='totp_secret'"))
        exists = result.fetchone() is not None
        
        if exists:
            print('✅ totp_secret column already exists')
        else:
            print('❌ totp_secret column does NOT exist')
            print('\nAvailable columns in users table:')
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY column_name"))
            for row in result:
                print(f'  - {row[0]}')
            
            print('\n🔧 Adding totp_secret column...')
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN totp_secret VARCHAR(32) NULL"))
                conn.commit()
                print('✅ totp_secret column added successfully!')
            except Exception as e:
                print(f'Error adding column: {e}')
                
except Exception as e:
    print(f'DB Error: {e}')
