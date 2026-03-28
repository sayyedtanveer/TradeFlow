import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/medtrack")
    await conn.execute("UPDATE tenants SET currency_code='INR', currency_symbol='₹' WHERE slug='synapse-mfg-v18'")
    await conn.close()
    print("DONE")

asyncio.run(main())
