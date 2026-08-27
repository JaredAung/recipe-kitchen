from functools import lru_cache

from supabase import Client, create_client

from recipe_kitchen.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client using the publishable key."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


@lru_cache
def get_supabase_admin() -> Client:
    """Return a cached Supabase client using the secret key (bypasses RLS)."""
    settings = get_settings()
    secret = settings.secret_key
    if not secret:
        raise RuntimeError("SUPABASE_SECRET_KEY is missing")
    return create_client(settings.supabase_url, secret)


def get_supabase_for_user(access_token: str) -> Client:
    """Return a Supabase client scoped to the caller's access token."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_publishable_key)
    client.auth.set_session(access_token, refresh_token="")
    return client
