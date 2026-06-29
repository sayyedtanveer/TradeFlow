import os
import sys
import asyncio

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
os.environ['DATABASE_SYNC_URL'] = 'postgresql://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from backend.app.infrastructure.persistence.database import Base, create_engine
import backend.app.infrastructure.persistence.models.tenant_model  # noqa: F401
import backend.app.infrastructure.persistence.models.user_model  # noqa: F401


async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('core_schema_created')


asyncio.run(main())
