import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.models.requirement import Requirement
from app.models.assessment import AssessmentJob, RequirementResult
from app.models.standard import Framework, Standard

async def reset_db():
    engine = create_async_engine("sqlite+aiosqlite:///./prs.db", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_db())
