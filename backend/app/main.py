"""FastAPI entrypoint for RootCause AI."""

import contextlib
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from backend.app.api.routes import diagnose, health, incidents
from backend.app.config import settings
from backend.app.db.database import engine


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for FastAPI startup and shutdown."""
    if settings.auto_create_db:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(
    title="RootCause AI API",
    description="Backend API for the RootCause AI automated diagnostics engine.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(diagnose.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
