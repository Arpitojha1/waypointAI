"""
Waypoint API — Step Feedback & Edit Routes

POST /api/steps/{id}/feedback - Submit status changes on roadmap steps:
  - DONE -> cognee.improve positive
  - REJECTED -> cognee.improve negative
  - SKIPPED -> cognee.forget
POST /api/steps/{id}/edit - Accept or Improve a step description edit
"""

import uuid
import logging
import asyncio
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Step, StepStatus
from app.auth.supabase import get_current_user, AuthenticatedUser
from app.memory.cognee_client import improve, forget

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/steps", tags=["feedback"])


class StepFeedbackRequest(BaseModel):
    status: StepStatus
    feedback_text: Optional[str] = None
    update_cognee: bool = True


class StepFeedbackResponse(BaseModel):
    id: uuid.UUID
    roadmap_id: uuid.UUID
    status: StepStatus
    is_memified: bool
    message: str


class StepEditRequest(BaseModel):
    description: str
    action: Literal["accept", "improve"]


class StepEditResponse(BaseModel):
    id: uuid.UUID
    description: str
    message: str


@router.post("/{id}/feedback", response_model=StepFeedbackResponse)
async def submit_step_feedback(
    id: uuid.UUID,
    payload: StepFeedbackRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update step status and trigger corresponding Cognee memory lifecycle action:
    - DONE: triggers cognee.improve (positive reinforcement)
    - REJECTED: triggers cognee.improve (negative reinforcement)
    - SKIPPED: triggers cognee.forget (removes stale step from memory)
    """
    stmt = select(Step).where(Step.id == id, Step.user_id == current_user.user_id)
    res = await db.execute(stmt)
    step = res.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {id} not found or access denied",
        )

    old_status = step.status
    step.status = payload.status

    msg = f"Updated step status from {old_status.value} to {payload.status.value}"

    if payload.update_cognee and old_status != payload.status:
        user_id_str = str(step.user_id)
        session_id = str(step.roadmap_id)

        try:
            if payload.status == StepStatus.DONE:
                await improve(
                    step_data={"title": step.title, "qa_id": str(step.id)},
                    outcome="positive",
                    session_id=session_id,
                    user_id=user_id_str,
                    dataset_name="step",
                )
                step.is_memified = True
                msg += " (triggered Cognee improve positive)"
            elif payload.status == StepStatus.REJECTED:
                await improve(
                    step_data={"title": step.title, "qa_id": str(step.id)},
                    outcome="negative",
                    session_id=session_id,
                    user_id=user_id_str,
                    dataset_name="step",
                )
                step.is_memified = True
                msg += " (triggered Cognee improve negative)"
            elif payload.status == StepStatus.SKIPPED:
                await forget(
                    data_id=str(step.id),
                    dataset_name="step",
                    user_id=user_id_str,
                )
                msg += " (triggered Cognee forget)"
        except Exception as exc:
            logger.warning("Cognee memory lifecycle call failed for step feedback: %s", exc)
            msg += f" (Cognee warning: {exc})"

    await db.commit()
    await db.refresh(step)

    return StepFeedbackResponse(
        id=step.id,
        roadmap_id=step.roadmap_id,
        status=step.status,
        is_memified=step.is_memified,
        message=msg,
    )


@router.post("/{id}/edit", response_model=StepEditResponse)
async def submit_step_edit(
    id: uuid.UUID,
    payload: StepEditRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 4: Accept or Improve a step description edit.
    - accept: saves edited text as-is, no Cognee call
    - improve: saves edited text AND feeds the diff (original → edited) into
      Cognee's improve() as a feedback signal, reusing the existing feedback path
    """
    stmt = select(Step).where(Step.id == id, Step.user_id == current_user.user_id)
    res = await db.execute(stmt)
    step = res.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {id} not found or access denied",
        )

    original_description = step.description or ""
    step.description = payload.description

    msg = "Step description updated"

    if payload.action == "improve" and original_description != payload.description:
        user_id_str = str(step.user_id)
        session_id = str(step.roadmap_id)

        try:
            # Feed the edit diff as positive feedback into Cognee's improve()
            # Reuses the same improve() path as step check-off feedback
            diff_text = (
                f"User edited step '{step.title}' description.\n"
                f"Original: {original_description[:300]}\n"
                f"Edited: {payload.description[:300]}"
            )
            await improve(
                step_data={
                    "title": step.title,
                    "qa_id": str(step.id),
                    "feedback_text": diff_text,
                },
                outcome="positive",
                session_id=session_id,
                user_id=user_id_str,
                dataset_name="step",
            )
            step.is_memified = True
            msg += " (triggered Cognee improve with edit diff)"
        except Exception as exc:
            logger.warning("Cognee improve failed for step edit: %s", exc)
            msg += f" (Cognee warning: {exc})"
    elif payload.action == "accept":
        msg += " (accepted as-is, no memory write)"

    await db.commit()
    await db.refresh(step)

    return StepEditResponse(
        id=step.id,
        description=step.description or "",
        message=msg,
    )
