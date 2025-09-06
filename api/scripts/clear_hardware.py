
import asyncio
import logging

from api.database import SessionLocal
from api.models import HardwareItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Clearing hardware items...")
    async with SessionLocal() as session:
        await session.execute(HardwareItem.__table__.delete())
        await session.commit()
    logger.info("Hardware items cleared.")

if __name__ == "__main__":
    asyncio.run(main())
