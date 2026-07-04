"""
Waypoint API — Auth & Profile Routes

POST /api/profile/seed - Seed/onboard user profile in Postgres and Cognee
GET /api/profile/me - Get current user's profile
"""

import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.db.models import UserProfile
from app.auth.supabase import get_current_user, AuthenticatedUser
from app.memory.cognee_client import remember

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileSeedRequest(BaseModel):
    display_name: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_summary: Optional[str] = None
    projects: List[Any] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    remember_in_cognee: bool = True


class BYOKRequest(BaseModel):
    byok_key: Optional[str] = None
    byok_model: Optional[str] = None
    byok_endpoint: Optional[str] = None


class BYOKResponse(BaseModel):
    byok_key: Optional[str] = None
    byok_model: Optional[str] = None
    byok_endpoint: Optional[str] = None


class ProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: Optional[str]
    skills: List[str]
    experience_summary: Optional[str]
    projects: List[Any]
    preferences: Dict[str, Any]
    byok_model: Optional[str] = None
    byok_endpoint: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/seed", response_model=ProfileResponse)
async def seed_profile(
    payload: ProfileSeedRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Seed or update the user's skill profile, experience, and preferences.
    Stores in Postgres and remembers in Cognee knowledge graph.
    """
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = UserProfile(
            user_id=current_user.user_id,
            display_name=payload.display_name or current_user.email or "Waypoint User",
            skills=payload.skills,
            experience_summary=payload.experience_summary,
            projects=payload.projects,
            preferences=payload.preferences,
        )
        db.add(profile)
    else:
        if payload.display_name is not None:
            profile.display_name = payload.display_name
        if payload.skills:
            profile.skills = payload.skills
        if payload.experience_summary is not None:
            profile.experience_summary = payload.experience_summary
        if payload.projects:
            profile.projects = payload.projects
        if payload.preferences:
            profile.preferences = payload.preferences

    await db.commit()
    await db.refresh(profile)

    if payload.remember_in_cognee:
        try:
            prof_dict = {
                "id": str(profile.id),
                "user_id": str(profile.user_id),
                "display_name": profile.display_name,
                "skills": profile.skills,
                "experience_summary": profile.experience_summary,
                "projects": profile.projects,
                "preferences": profile.preferences,
            }
            await remember(
                data=prof_dict,
                data_type="user_profile",
                dataset_name=f"{str(profile.user_id)}_user_profile",
            )
        except Exception as exc:
            logger.warning("Failed to remember user profile in Cognee: %s", exc)

    return profile


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the currently authenticated user's profile.
    """
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Call POST /api/profile/seed first.",
        )

    return profile


@router.get("/byok", response_model=BYOKResponse)
async def get_byok_settings(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the user's BYOK settings (decrypting the key using pgcrypto if present).
    """
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        return BYOKResponse()

    byok_key_str = None
    if profile.byok_key_encrypted:
        try:
            stmt_dec = select(func.pgp_sym_decrypt(profile.byok_key_encrypted, settings.MASTER_KEY))
            res_dec = await db.execute(stmt_dec)
            byok_key_str = res_dec.scalar_one_or_none()
        except Exception as exc:
            logger.warning("Failed to decrypt BYOK key for user %s: %s", current_user.user_id, exc)

    return BYOKResponse(
        byok_key=byok_key_str,
        byok_model=profile.byok_model,
        byok_endpoint=profile.byok_endpoint,
    )


@router.post("/byok", response_model=BYOKResponse)
async def save_byok_settings(
    payload: BYOKRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save or update user's BYOK settings (encrypting key with pgcrypto via SQL).
    """
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        profile = UserProfile(
            user_id=current_user.user_id,
            display_name=current_user.email or "Waypoint User",
        )
        db.add(profile)

    if payload.byok_model is not None:
        profile.byok_model = payload.byok_model.strip() if payload.byok_model else None
    if payload.byok_endpoint is not None:
        profile.byok_endpoint = payload.byok_endpoint.strip() if payload.byok_endpoint else None

    if payload.byok_key is not None:
        key_val = payload.byok_key.strip()
        if key_val:
            stmt_enc = select(func.pgp_sym_encrypt(key_val, settings.MASTER_KEY))
            res_enc = await db.execute(stmt_enc)
            profile.byok_key_encrypted = res_enc.scalar_one()
        else:
            profile.byok_key_encrypted = None

    await db.commit()
    await db.refresh(profile)

    byok_key_str = None
    if profile.byok_key_encrypted:
        try:
            stmt_dec = select(func.pgp_sym_decrypt(profile.byok_key_encrypted, settings.MASTER_KEY))
            res_dec = await db.execute(stmt_dec)
            byok_key_str = res_dec.scalar_one_or_none()
        except Exception as exc:
            logger.warning("Failed to decrypt BYOK key after save: %s", exc)

    return BYOKResponse(
        byok_key=byok_key_str,
        byok_model=profile.byok_model,
        byok_endpoint=profile.byok_endpoint,
    )


@router.get("/token", response_model=Dict[str, str])
async def get_test_token():
    """
    Development/Demo helper: get a valid JWT token for testing.
    Gated: Only works when ENABLE_BACKEND_ACCESS_CONTROL="false".
    """
    if os.environ.get("ENABLE_BACKEND_ACCESS_CONTROL", "true").lower() != "false":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development token endpoint is disabled when access control is enabled."
        )

    import time
    from jose import jwt
    from app.config import settings

    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    payload = {
        "sub": str(user_id),
        "email": "dev@waypoint.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 86400 * 30,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "user_id": str(user_id)}
