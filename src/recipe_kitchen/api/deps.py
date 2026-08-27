from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from recipe_kitchen.core.config import get_settings

bearer = HTTPBearer(auto_error=True)


@lru_cache
def _jwks_client() -> PyJWKClient:
    """Return a cached JWKS client for verifying Supabase access tokens."""
    return PyJWKClient(get_settings().jwks_url)


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a Supabase JWT. Raises PyJWTError on failure."""
    settings = get_settings()
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
        options={"require": ["exp", "sub"]},
    )


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict[str, Any]:
    """FastAPI dependency that returns the authenticated user claims."""
    try:
        return verify_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc
