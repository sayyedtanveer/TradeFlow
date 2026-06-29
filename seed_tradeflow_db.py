import os
import sys
import asyncio
import uuid
from datetime import datetime, timezone

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
os.environ['DATABASE_SYNC_URL'] = 'postgresql://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from backend.app.infrastructure.persistence.database import Base, create_engine
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('schema_created')

    async_engine = create_async_engine(os.environ['DATABASE_URL'])
    async with async_engine.begin() as conn:
        tenant_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        hashed_password = BcryptPasswordHasher().hash('Admin@123456')

        await conn.execute(text("DELETE FROM users WHERE email = :email"), {'email': 'admin@tradeflow.local'})
        await conn.execute(text("DELETE FROM tenants WHERE slug = :slug"), {'slug': 'tradeflow-demo'})

        await conn.execute(
            text(
                """
                INSERT INTO tenants (
                    id, name, slug, plan, is_active, is_deleted,
                    currency_code, currency_symbol, company_name, email,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :slug, :plan, :is_active, :is_deleted,
                    :currency_code, :currency_symbol, :company_name, :email,
                    :created_at, :updated_at
                )
                """
            ),
            {
                'id': tenant_id,
                'name': 'TradeFlow Demo',
                'slug': 'tradeflow-demo',
                'plan': 'starter',
                'is_active': True,
                'is_deleted': False,
                'currency_code': 'INR',
                'currency_symbol': '₹',
                'company_name': 'TradeFlow Demo',
                'email': 'admin@tradeflow.local',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
            },
        )

        await conn.execute(
            text(
                """
                INSERT INTO users (
                    id, tenant_id, email, hashed_password, first_name, last_name,
                    role, is_active, is_deleted, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :email, :hashed_password, :first_name, :last_name,
                    :role, :is_active, :is_deleted, :created_at, :updated_at
                )
                """
            ),
            {
                'id': user_id,
                'tenant_id': tenant_id,
                'email': 'admin@tradeflow.local',
                'hashed_password': hashed_password,
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'tenant_admin',
                'is_active': True,
                'is_deleted': False,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
            },
        )
        print('seeded', tenant_id, user_id)

    await async_engine.dispose()


asyncio.run(main())
