"""
Waypoint API — Supabase Auth Dependency

Verifies Supabase JWTs and extracts the authenticated user_id.
Used as a FastAPI dependency for protected endpoints.

Supabase now issues ES256-signed JWTs verified via a per-project JWKS
endpoint, rather than a single shared HS256 secret. This module fetches
and caches the public signing key from Supabase's JWKS endpoint.
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
import jwt as pyjwt
from jwt.exceptions import PyJWTError

from app.config import settings

import os

# Bearer token extractor
security = HTTPBearer(auto_error=False)

AUDIENCE = "authenticated"

# Cached JWKS client — fetches and caches Supabase's public signing keys
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


class AuthenticatedUser:
    """Lightweight container for the authenticated user's identity."""

    def __init__(self, user_id: uuid.UUID, email: Optional[str] = None, role: str = "authenticated"):
        self.user_id = user_id
        self.email = email
        self.role = role

    def __repr__(self) -> str:
        return f"AuthenticatedUser(user_id={self.user_id}, email={self.email})"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency: decode & verify a Supabase JWT via JWKS.

    Returns an AuthenticatedUser with user_id (sub claim).
    Raises 401 if the token is missing, expired, or invalid.
    Bypasses auth if ENABLE_BACKEND_ACCESS_CONTROL is set to 'false'.
    """
    if os.environ.get("ENABLE_BACKEND_ACCESS_CONTROL", "true").lower() == "false":
        return AuthenticatedUser(
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="dev@waypoint.local",
            role="authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not credentials.credentials:
        raise credentials_exception

    token = credentials.credentials

    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=AUDIENCE,
        )

        sub: Optional[str] = payload.get("sub")
        if sub is None:
            raise credentials_exception

        user_id = uuid.UUID(sub)
        email = payload.get("email")
        role = payload.get("role", "authenticated")

        return AuthenticatedUser(user_id=user_id, email=email, role=role)

    except (PyJWTError, ValueError) as e:
        raise credentials_exception from e