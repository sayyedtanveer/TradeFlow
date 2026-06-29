import os
import sys
import asyncio
import subprocess

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:123@localhost:5432/tradeflow'
sys.path.insert(0, '.')

from sqlalchemy import text, inspect
from backend.app.infrastructure.persistence.database import create_engine

async def main() -> None:
    engine = create_engine(os.environ['DATABASE_URL'])
    
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Tables created ({len(tables)}):")
        for t in sorted(tables):
            print(f"  {t}")

asyncio.run(main())
