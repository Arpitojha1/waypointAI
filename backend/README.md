# Waypoint — Backend API

FastAPI backend and Cognee memory orchestrator for Waypoint.

## Quick Setup

### Database Schema Initialization

You can initialize the database schema in two ways:

#### Option 1: Alembic Migrations (Recommended for development & schema changes)
If you have your Python environment set up:
```bash
alembic upgrade head
```

#### Option 2: Standalone Plain SQL (Quick Setup without Python environment)
As an alternative to `alembic upgrade head`, if you want to inspect or load the schema directly without setting up the Python environment first:
```bash
psql $DATABASE_URL -f sql/schema.sql
```
To load sample test data for sanity-checking without running the application:
```bash
psql $DATABASE_URL -f sql/seed.sql
```

> **Note on schema maintenance:** `sql/schema.sql` is a convenience snapshot generated from Alembic migrations (`alembic upgrade head --sql`). Alembic remains the authoritative source of truth for schema changes going forward.

## Running Locally

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your API keys and Supabase credentials:
   ```bash
   cp .env.example .env
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
