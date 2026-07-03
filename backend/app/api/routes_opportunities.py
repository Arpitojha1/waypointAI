"""
Waypoint API — Opportunity Routes

GET /api/opportunities - List opportunities with type filter and pagination
GET /api/opportunities/{id} - Get specific opportunity details
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Opportunity, OpportunityType
from app.ingestion import verify_github_issue_open

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    type: OpportunityType
    title: str
    description: Optional[str]
    url: Optional[str]
    source: Optional[str]
    metadata_: Optional[Dict[str, Any]] = None
    repo_owner: Optional[str] = None
    repo_name: Optional[str] = None
    issue_number: Optional[int] = None
    company: Optional[str] = None
    location: Optional[str] = None
    deadline: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

    @classmethod
    def from_orm_obj(cls, obj: Opportunity):
        return cls(
            id=obj.id,
            type=obj.type,
            title=obj.title,
            description=obj.description,
            url=obj.url,
            source=obj.source,
            metadata_=obj.metadata_,
            repo_owner=obj.repo_owner,
            repo_name=obj.repo_name,
            issue_number=obj.issue_number,
            company=obj.company,
            location=obj.location,
            deadline=obj.deadline,
            is_active=obj.is_active,
            created_at=obj.created_at,
        )


@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    type_filter: Optional[OpportunityType] = Query(None, alias="type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List career opportunities with optional filtering by type (job, hackathon, issue)
    and pagination support, with deduplication for multiple ingestion passes.
    """
    stmt = select(Opportunity).where(Opportunity.is_active == True)
    if type_filter:
        stmt = stmt.where(Opportunity.type == type_filter)
    
    stmt = stmt.order_by(Opportunity.created_at.desc())
    res = await db.execute(stmt)
    all_opps = res.scalars().all()

    # Deduplicate server-side (in case multiple ingestion runs inserted the same opportunity)
    unique_opps = []
    seen = set()
    for o in all_opps:
        dedup_key = (o.type, (o.url or "").lower().strip(), o.title.lower().strip())
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique_opps.append(o)

    paginated_opps = unique_opps[offset:offset + limit]

    # Re-verify GitHub issue status before display
    verified_opps = []
    has_changes = False
    async with httpx.AsyncClient(timeout=5.0) as client:
        for o in paginated_opps:
            if o.type == OpportunityType.ISSUE and o.repo_owner and o.repo_name and o.issue_number:
                is_open = await verify_github_issue_open(
                    owner=o.repo_owner,
                    repo=o.repo_name,
                    issue_number=o.issue_number,
                    client=client,
                )
                if not is_open:
                    o.is_active = False
                    has_changes = True
                    continue
            verified_opps.append(o)
    if has_changes:
        await db.commit()

    return [OpportunityResponse.from_orm_obj(o) for o in verified_opps]


@router.get("/{id}", response_model=OpportunityResponse)
async def get_opportunity(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific career opportunity by ID.
    """
    stmt = select(Opportunity).where(Opportunity.id == id)
    res = await db.execute(stmt)
    opp = res.scalar_one_or_none()

    if not opp or not opp.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity {id} not found",
        )

    if opp.type == OpportunityType.ISSUE and opp.repo_owner and opp.repo_name and opp.issue_number:
        async with httpx.AsyncClient(timeout=5.0) as client:
            is_open = await verify_github_issue_open(
                owner=opp.repo_owner,
                repo=opp.repo_name,
                issue_number=opp.issue_number,
                client=client,
            )
            if not is_open:
                opp.is_active = False
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Opportunity {id} is no longer active (closed on GitHub)",
                )

    return OpportunityResponse.from_orm_obj(opp)
