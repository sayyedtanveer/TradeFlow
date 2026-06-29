import os
import sys
import uuid
import asyncio
import json

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
os.environ['DATABASE_SYNC_URL'] = 'postgresql://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.app.application.tenant.commands.login_user import LoginUserCommand
from backend.app.application.tenant.handlers.login_user_handler import LoginUserHandler
from backend.app.infrastructure.persistence.database import create_engine, Base
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel
from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.infrastructure.security.jwt_handler import JWTHandler
from backend.app.infrastructure.security.password_hasher import BcryptPasswordHasher

# Import all models to ensure metadata is fully populated
import backend.app.infrastructure.persistence.models.supplier_model  # noqa: F401


async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Check if tenant exists
        result = await session.execute(select(TenantModel).where(TenantModel.slug == 'tradeflow'))
        tenant = result.scalar_one_or_none()
        
        # If not, create via raw SQL to avoid ORM FK validation
        if not tenant:
            tenant_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, plan, is_active, currency_code, currency_symbol, company_name, email, created_at, updated_at, is_deleted)
                    VALUES (:id, :name, :slug, :plan, :is_active, :currency_code, :currency_symbol, :company_name, :email, now(), now(), false)
                """),
                {
                    "id": tenant_id,
                    "name": "TradeFlow",
                    "slug": "tradeflow",
                    "plan": "starter",
                    "is_active": True,
                    "currency_code": "USD",
                    "currency_symbol": "$",
                    "company_name": "TradeFlow",
                    "email": "admin@tradeflow.local",
                }
            )
            await session.commit()
            result = await session.execute(select(TenantModel).where(TenantModel.slug == 'tradeflow'))
            tenant = result.scalar_one_or_none()
        
        # Check if user exists
        result = await session.execute(select(UserModel).where(UserModel.email == 'admin@tradeflow.local'))
        user = result.scalar_one_or_none()
        
        if not user:
            hasher = BcryptPasswordHasher()
            user_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, hashed_password, first_name, last_name, role, is_active, totp_enabled, backup_codes, created_at, updated_at, is_deleted)
                    VALUES (:id, :tenant_id, :email, :hashed_password, :first_name, :last_name, :role, :is_active, :totp_enabled, :backup_codes, now(), now(), false)
                """),
                {
                    "id": user_id,
                    "tenant_id": str(tenant.id),
                    "email": "admin@tradeflow.local",
                    "hashed_password": hasher.hash('Admin@123456'),
                    "first_name": "Admin",
                    "last_name": "User",
                    "role": "admin",
                    "is_active": True,
                    "totp_enabled": False,
                    "backup_codes": json.dumps([]),
                }
            )
            await session.commit()
            result = await session.execute(select(UserModel).where(UserModel.email == 'admin@tradeflow.local'))
            user = result.scalar_one_or_none()
        
        # Now test login
        user_repo = UserRepository(session)
        handler = LoginUserHandler(
            user_repo=user_repo,
            password_hasher=BcryptPasswordHasher(),
            jwt_handler=JWTHandler(secret_key='change-me-to-a-long-random-secret-at-least-32-chars', algorithm='HS256', expiry_minutes=60),
        )
        result = await handler.handle(LoginUserCommand(email='admin@tradeflow.local', password='Admin@123456', tenant_id=tenant.id))
        print('✓ Seeding complete')
        print('  tenant_id:', str(tenant.id))
        print('  user_id:', result.user_id)
        print('  role:', result.role)
        print('  login_ok:', bool(result.access_token))
        print()
        print('Login credentials:')
        print('  Email: admin@tradeflow.local')
        print('  Password: Admin@123456')


asyncio.run(main())
