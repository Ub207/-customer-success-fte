import asyncio
import asyncpg
import pathlib
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    sql = pathlib.Path("database/schema.sql").read_text()
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(sql)
    await conn.close()
    print("Schema applied successfully!")

asyncio.run(run())
