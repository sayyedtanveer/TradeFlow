import os
import sys
import asyncio

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
os.environ['DATABASE_SYNC_URL'] = 'postgresql://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from backend.app.infrastructure.persistence.database import Base, create_engine
from backend.app.infrastructure.persistence.models.tenant_model import TenantModel
from backend.app.infrastructure.persistence.models.user_model import UserModel, PasswordResetTokenModel, ClientNotificationSettingsModel


async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('auth_schema_created')


asyncio.run(main())
