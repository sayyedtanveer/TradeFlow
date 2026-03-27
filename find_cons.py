import asyncio
from backend.app.config import get_settings
from backend.app.infrastructure.persistence.database import create_engine
from sqlalchemy import text

async def main():
    engine = create_engine(get_settings().database_url)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'workstations';"))
        print([r[0] for r in res])
    await engine.dispose()

asyncio.run(main())
