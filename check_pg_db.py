import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db():
    try:
        engine = create_async_engine('postgresql+asyncpg://postgres:123@localhost:5432/medtrack')
        async with engine.begin() as conn:
            # Check if tenants table exists
            result = await conn.execute(sa.text('SELECT count(*) FROM tenants'))
            count = result.scalar()
            print(f'Tenants count: {count}')
            
            # Get tenants
            result = await conn.execute(sa.text('SELECT id, name FROM tenants LIMIT 5'))
            print("\n=== TENANTS ===")
            for row in result:
                print(f'ID: {row[0]}, Name: {row[1]}')
            
            # Get admin users
            result = await conn.execute(sa.text("SELECT id, email, tenant_id FROM users WHERE email LIKE '%admin%' LIMIT 5"))
            print("\n=== ADMIN USERS ===")
            for row in result:
                print(f'ID: {row[0]}, Email: {row[1]}, Tenant ID: {row[2]}')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

asyncio.run(check_db())
