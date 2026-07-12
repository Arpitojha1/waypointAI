"""
Waypoint API — SQLAlchemy Models

Shared schema for all 3 opportunity types (job, hackathon, issue).
RLS-ready: every user-scoped table has a `user_id` column that references
Supabase's `auth.users(id)`.

Per AGENT.md: one Roadmap + Step schema for all types — only the system
prompt and recall query differ per type, not the table structure.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Enum as SAEnum,
    func,
    LargeBinary,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

import enum


class OpportunityType(str, enum.Enum):
    JOB = "job"
    HACKATHON = "hackathon"
    ISSUE = "issue"


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    REJECTED = "rejected"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

class UserProfile(Base):
    """
    User's skill profile, experience, and preferences.
    Seeded via POST /api/profile/seed, stored in both Postgres (for joins)
    and Cognee (for recall during roadmap generation).
    """
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # FK to Supabase auth.users — enables RLS
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    skills: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    experience_summary: Mapped[Optional[str]] = mapped_column(Text)
    projects: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    byok_key_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    byok_model: Mapped[Optional[str]] = mapped_column(String(255))
    byok_endpoint: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roadmaps: Mapped[List["Roadmap"]] = relationship(
        back_populates="user_profile", foreign_keys="Roadmap.user_id",
        primaryjoin="UserProfile.user_id == Roadmap.user_id",
    )


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------

class Opportunity(Base):
    """
    A career opportunity: GitHub issue, Devpost hackathon, or Arbeitnow job.
    Ingested from external sources and stored in both Postgres and Cognee.
    """
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[OpportunityType] = mapped_column(
        SAEnum(OpportunityType, name="opportunity_type", values_callable=lambda obj: [e.value for e in obj], create_constraint=True),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(2048))
    source: Mapped[Optional[str]] = mapped_column(String(100))  # "github", "devpost", "arbeitnow"

    # Type-specific metadata (skills, labels, deadline, company, etc.)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)

    # For GitHub issues
    repo_owner: Mapped[Optional[str]] = mapped_column(String(255))
    repo_name: Mapped[Optional[str]] = mapped_column(String(255))
    issue_number: Mapped[Optional[int]] = mapped_column(Integer)

    # For jobs
    company: Mapped[Optional[str]] = mapped_column(String(500))
    location: Mapped[Optional[str]] = mapped_column(String(500))

    # For hackathons
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status tracking
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roadmaps: Mapped[List["Roadmap"]] = relationship(back_populates="opportunity")


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

class Roadmap(Base):
    """
    A generated plan for pursuing an opportunity.
    One Roadmap per (user, opportunity) pair.
    """
    __tablename__ = "roadmaps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # Track generation version for memify comparison
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Phase 3: Track whether Cognee memory seeding is complete for this roadmap
    cognee_seeded: Mapped[bool] = mapped_column(default=False, server_default=text('false'))

    # Track whether roadmap steps were synthetically generated (LLM fallback)
    is_synthetic_fallback: Mapped[bool] = mapped_column(default=False, server_default=text('false'))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    opportunity: Mapped["Opportunity"] = relationship(back_populates="roadmaps")
    steps: Mapped[List["Step"]] = relationship(
        back_populates="roadmap", order_by="Step.order_index"
    )
    user_profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="roadmaps", foreign_keys=[user_id],
        primaryjoin="Roadmap.user_id == UserProfile.user_id",
    )


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

class Step(Base):
    """
    A single action item within a Roadmap.
    Status changes trigger Cognee improve/forget calls.
    """
    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized user_id for RLS — avoids join through roadmap for every policy check
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[StepStatus] = mapped_column(
        SAEnum(StepStatus, name="step_status", values_callable=lambda obj: [e.value for e in obj], create_constraint=True),
        default=StepStatus.PENDING,
    )

    # Resource links (curated by the resource-finder role)
    resource_links: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # Memify tracking — set to True when Cognee improve() changes this step's rank
    is_memified: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    roadmap: Mapped["Roadmap"] = relationship(back_populates="steps")
