"""Scrape a Facebook reel or post with Apify and return the raw dataset."""

from __future__ import annotations

from pathlib import Path

from apify_client import ApifyClient

from recipe_kitchen.utils import load_env, require_api_key

ROOT = Path(__file__).resolve().parents[4]
ACTOR_ID = "apify/facebook-posts-scraper"


def fetch_facebook(
    facebook_url: str,
    *,
    api_token: str | None = None,
) -> list[dict]:
    """Scrape `facebook_url` with Apify and return the raw dataset items.

    Raises RuntimeError when the token is missing, the actor fails, or
    the dataset is empty.
    """
    load_env(ROOT / ".env")
    client = ApifyClient(require_api_key(api_token, name="APIFY_API_TOKEN"))
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
