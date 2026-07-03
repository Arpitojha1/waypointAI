"""
Waypoint API — Application Settings

Pydantic Settings: reads from environment variables / .env file.
All sensitive values (keys, DB URL) come from env — never hardcoded.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Waypoint API"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Supabase ---
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str  # used to verify JWTs server-side

    # --- Database (Postgres via Supabase or standalone) ---
    DATABASE_URL: str  # asyncpg format: postgresql+asyncpg://user:pass@host:port/db

    # --- Cognee ---
    COGNEE_API_KEY: str = ""  # Cognee Cloud key, if using hosted
    COGNEE_LLM_API_KEY: str = ""  # LLM provider key for Cognee's internal use
    COGNEE_LLM_PROVIDER: str = "openrouter"  # or "anthropic", "openai"
    COGNEE_LLM_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"  # model Cognee uses internally
    COGNEE_VECTOR_DB: str = "lancedb"  # default local vector store

    # --- OpenRouter (BYOK fallback) ---
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # --- Anthropic (primary LLM for orchestrator) ---
    ANTHROPIC_API_KEY: str = ""

    # --- Encryption ---
    MASTER_KEY: str  # AES-256 key for pgcrypto BYOK encryption

    model_config = {
        "env_file": (".env", "backend/.env", "../.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
