from typing import Annotated, Any

from fastapi import APIRouter, Depends

from recipe_kitchen.api.deps import get_current_user
from recipe_kitchen.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, bool]:
    """Return process liveness and whether Supabase credentials are configured."""
    settings = get_settings()
    return {
        "ok": True,
        "supabase": bool(settings.supabase_url and settings.secret_key),
    }


@router.get("/me")
def me(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, Any]:
    """Return the authenticated user's subject and role from the access token."""
    return {"sub": user.get("sub"), "role": user.get("role")}
