# API routes module
from app.api.routes_auth import router as auth_router
from app.api.routes_opportunities import router as opportunities_router
from app.api.routes_roadmap import router as roadmap_router
from app.api.routes_feedback import router as feedback_router

__all__ = [
    "auth_router",
    "opportunities_router",
    "roadmap_router",
    "feedback_router",
]
