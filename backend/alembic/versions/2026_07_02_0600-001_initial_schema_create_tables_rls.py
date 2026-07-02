"""Initial schema: UserProfile, Opportunity, Roadmap, Step + RLS policies

Revision ID: 001
Revises: None
Create Date: 2026-07-02

Creates all Phase 1 tables and enables Row Level Security (RLS)
on user-scoped tables (user_profiles, roadmaps, steps).

RLS policies use auth.uid() from Supabase's auth system to scope
all queries to the authenticated user.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enable pgcrypto extension (for BYOK encryption in Phase 8) ---
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --- Enum types ---
    opportunity_type = postgresql.ENUM(
        "job", "hackathon", "issue",
        name="opportunity_type",
        create_type=True,
    )
    step_status = postgresql.ENUM(
        "pending", "done", "rejected", "skipped",
        name="step_status",
        create_type=True,
    )
    opportunity_type.create(op.get_bind(), checkfirst=True)
    step_status.create(op.get_bind(), checkfirst=True)

    # --- user_profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(255)),
        sa.Column("skills", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("experience_summary", sa.Text),
        sa.Column("projects", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("preferences", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- opportunities ---
    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", opportunity_type, nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("url", sa.String(2048)),
        sa.Column("source", sa.String(100)),
        sa.Column("metadata", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("repo_owner", sa.String(255)),
        sa.Column("repo_name", sa.String(255)),
        sa.Column("issue_number", sa.Integer),
        sa.Column("company", sa.String(500)),
        sa.Column("location", sa.String(500)),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- roadmaps ---
    op.create_table(
        "roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("version", sa.Integer, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- steps ---
    op.create_table(
        "steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("roadmap_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("order_index", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", step_status, server_default=sa.text("'pending'")),
        sa.Column("resource_links", postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_memified", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # Row Level Security (RLS) Policies
    # Per AGENT.md: "RLS enabled on every user-scoped table"
    # Policy keyed to auth.uid() — Supabase's built-in function
    # ═══════════════════════════════════════════════════════════════════

    # --- user_profiles RLS ---
    op.execute("ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_profiles_select ON user_profiles
            FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_profiles_insert ON user_profiles
            FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_profiles_update ON user_profiles
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_profiles_delete ON user_profiles
            FOR DELETE USING (user_id = auth.uid())
    """)

    # --- roadmaps RLS ---
    op.execute("ALTER TABLE roadmaps ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY roadmaps_select ON roadmaps
            FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY roadmaps_insert ON roadmaps
            FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY roadmaps_update ON roadmaps
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY roadmaps_delete ON roadmaps
            FOR DELETE USING (user_id = auth.uid())
    """)

    # --- steps RLS (uses denormalized user_id to avoid joins) ---
    op.execute("ALTER TABLE steps ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY steps_select ON steps
            FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY steps_insert ON steps
            FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY steps_update ON steps
            FOR UPDATE USING (user_id = auth.uid())
            WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY steps_delete ON steps
            FOR DELETE USING (user_id = auth.uid())
    """)

    # --- opportunities: NO RLS (shared across all users) ---
    # Opportunities are public data ingested from GitHub/Devpost/Arbeitnow.
    # No user_id column, no RLS needed.


def downgrade() -> None:
    # Drop RLS policies
    for table in ["steps", "roadmaps", "user_profiles"]:
        for action in ["select", "insert", "update", "delete"]:
            op.execute(f"DROP POLICY IF EXISTS {table}_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Drop tables
    op.drop_table("steps")
    op.drop_table("roadmaps")
    op.drop_table("opportunities")
    op.drop_table("user_profiles")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS step_status")
    op.execute("DROP TYPE IF EXISTS opportunity_type")
