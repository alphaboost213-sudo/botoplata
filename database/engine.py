from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import config
from database.models import Base

engine = create_async_engine(config.DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from database.requests import seed_default_directions
    await seed_default_directions()
