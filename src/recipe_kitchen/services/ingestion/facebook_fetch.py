"""Scrape a Facebook reel or post with Apify and return the raw dataset."""

from __future__ import annotations

import os
from pathlib import Path

from apify_client import ApifyClient

ROOT = Path(__file__).resolve().parents[4]
ACTOR_ID = "apify/facebook-posts-scraper"


def _load_env(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ if the file exists.

    Existing environment variables are not overwritten.
    """
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _require_token(api_token: str | None) -> str:
    """Return `api_token` or APIFY_API_TOKEN from the environment.

    Raises RuntimeError if neither is set.
    """
    token = (api_token or os.environ.get("APIFY_API_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("APIFY_API_TOKEN is missing. Set it in .env")
    return token


def fetch_facebook(
    facebook_url: str,
    *,
    api_token: str | None = None,
) -> list[dict]:
    """Scrape `facebook_url` with Apify and return the raw dataset items.

    Raises RuntimeError when the token is missing, the actor fails, or
    the dataset is empty.
    """
    _load_env(ROOT / ".env")
    client = ApifyClient(_require_token(api_token))
    run = client.actor(ACTOR_ID).call(
        run_input={
            "startUrls": [{"url": facebook_url}],
            "resultsLimit": 1,
            "captionText": False,
        }
    )
    if not run:
        raise RuntimeError("Apify actor run failed.")

    dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    items = list(client.dataset(dataset_id).iterate_items())
    if not items:
        raise RuntimeError("Actor returned no posts.")
    return items
