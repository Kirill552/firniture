import asyncio, asyncpg
async def main():
    conn = await asyncpg.connect(user='app', password='app', database='furniture_ai', host='127.0.0.1', port=5432)
    v = await conn.fetchval('select 1')
    print('ok', v)
    await conn.close()
asyncio.run(main())
