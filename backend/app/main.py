"""
Waypoint API — FastAPI Application

Phase 1: backend skeleton with health check, CORS, lifespan.
Router registrations are added as route modules are built.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db, close_db
from app.memory.cognee_client import configure_cognee


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle manager."""
    # Startup: verify DB connectivity
    await init_db()
    # Configure Cognee memory system
    if settings.COGNEE_LLM_API_KEY:
        await configure_cognee(
            llm_api_key=settings.COGNEE_LLM_API_KEY,
            llm_provider=settings.COGNEE_LLM_PROVIDER,
            llm_model=settings.COGNEE_LLM_MODEL,
        )
    yield
    # Shutdown: dispose connection pool
    await close_db()


app = FastAPI(
    title="Waypoint API",
    description="Career Opportunity Agent with Cognee Memory — Cognee Hackathon",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "waypoint-api"}


from app.api import (
    auth_router,
    opportunities_router,
    roadmap_router,
    feedback_router,
)

# --- Routers ---
app.include_router(auth_router)
app.include_router(opportunities_router)
app.include_router(roadmap_router)
app.include_router(feedback_router)