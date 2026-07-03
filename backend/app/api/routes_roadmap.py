"""
Waypoint API — Roadmap Routes

POST /api/roadmaps - Generate a new roadmap for an opportunity
GET /api/roadmaps/{id} - Fetch an existing roadmap and its steps
GET /api/roadmaps/by-opportunity/{opportunity_id} - Check for existing roadmap
"""

import uuid
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Roadmap, Step, StepStatus
from app.auth.supabase import get_current_user, AuthenticatedUser
from app.agents.orchestrator import generate_roadmap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/roadmaps", tags=["roadmaps"])


class GenerateRoadmapRequest(BaseModel):
    opportunity_id: uuid.UUID
    remember_in_cognee: bool = True
    force_regenerate: bool = False


class StepResponse(BaseModel):
    id: uuid.UUID
    roadmap_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str]
    order_index: int
    status: StepStatus
    resource_links: Optional[List[Dict[str, str]]] = None
    is_memified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RoadmapResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    opportunity_id: uuid.UUID
    title: str
    summary: Optional[str]
    version: int
    created_at: datetime
    steps: List[StepResponse] = []

    class Config:
        from_attributes = True


@router.get("/by-opportunity/{opportunity_id}", response_model=RoadmapResponse)
async def get_roadmap_by_opportunity(
    opportunity_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check for an existing roadmap for the given (user_id, opportunity_id) pair.
    Returns the roadmap if found, or 404 if no roadmap exists yet.
    This is a fast DB-only read — no LLM, no Cognee.
    """
    t0 = time.perf_counter()
    stmt = (
        select(Roadmap)
        .options(selectinload(Roadmap.steps))
        .where(
            Roadmap.user_id == current_user.user_id,
            Roadmap.opportunity_id == opportunity_id,
        )
        .order_by(Roadmap.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    roadmap = res.scalar_one_or_none()
    logger.info("PERF: [ROADMAP_CACHE_CHECK] %.3fs found=%s", time.perf_counter() - t0, roadmap is not None)

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existing roadmap for this opportunity",
        )

    if roadmap.steps:
        roadmap.steps.sort(key=lambda s: s.order_index)

    return roadmap


@router.post("", response_model=RoadmapResponse, status_code=status.HTTP_201_CREATED)
async def create_roadmap_endpoint(
    payload: GenerateRoadmapRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI roadmap and milestone steps for the specified opportunity.
    Uses Cognee memory recall + OpenAI tool-use loop.

    Phase 1 optimization: checks for existing roadmap first (unless force_regenerate=True).
    """
    is_first_generation = True

    # Phase 1: Check for existing roadmap before invoking the orchestrator
    if not payload.force_regenerate:
        t0 = time.perf_counter()
        stmt = (
            select(Roadmap)
            .options(selectinload(Roadmap.steps))
            .where(
                Roadmap.user_id == current_user.user_id,
                Roadmap.opportunity_id == payload.opportunity_id,
            )
            .order_by(Roadmap.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        logger.info("PERF: [ROADMAP_CACHE_CHECK] %.3fs found=%s", time.perf_counter() - t0, existing is not None)

        if existing:
            if existing.steps:
                existing.steps.sort(key=lambda s: s.order_index)
            # Return 200 (not 201) — we didn't create anything new
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=RoadmapResponse.model_validate(existing).model_dump(mode="json"),
            )
        # No existing roadmap — this is a first generation
        is_first_generation = True
    else:
        # force_regenerate=True — this is a regeneration
        is_first_generation = False

    try:
        roadmap = await generate_roadmap(
            session=db,
            user_id=current_user.user_id,
            opportunity_id=payload.opportunity_id,
            remember_in_cognee=payload.remember_in_cognee,
            is_first_generation=is_first_generation,
        )
        return roadmap
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {exc}",
        )


@router.get("/{id}", response_model=RoadmapResponse)
async def get_roadmap_endpoint(
    id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch an existing roadmap along with all its sequential steps.
    Protected by RLS user_id check.
    """
    stmt = (
        select(Roadmap)
        .options(selectinload(Roadmap.steps))
        .where(Roadmap.id == id, Roadmap.user_id == current_user.user_id)
    )
    res = await db.execute(stmt)
    roadmap = res.scalar_one_or_none()

    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roadmap {id} not found or access denied",
        )

    # Ensure steps are sorted by order_index
    if roadmap.steps:
        roadmap.steps.sort(key=lambda s: s.order_index)

    return roadmap
