from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.standards import router as standards_router
from app.api.documents import router as documents_router
from app.api.assessments import router as assessments_router

# Import models to ensure they are registered with Base.metadata
import app.models.standard
import app.models.requirement
import app.models.assessment
import app.models.document

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup DB tables (for now, avoiding alembic for rapid dev)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="PRS Compliance Intelligence API", version="1.0.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app.include_router(standards_router, prefix="/api/v1", tags=["Standards"])
app.include_router(documents_router, prefix="/api/v1", tags=["Documents"])
app.include_router(assessments_router, prefix="/api/v1", tags=["Assessments"])

# Removed static frontend serve


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
