"""Scrape a Facebook reel with Apify and download the HD MP4."""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from apify_client import ApifyClient

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).resolve().parent / "video.mp4"
ACTOR_ID = "apify/facebook-posts-scraper"
REEL_URL = "https://www.facebook.com/reel/1033484732739023"


def load_env(path: Path) -> None:
    """Load KEY=VALUE lines from `path` into os.environ if the file exists."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_token() -> str:
    """Return APIFY_API_TOKEN from the environment."""
    token = os.environ.get("APIFY_API_TOKEN", "").strip()
    if not token:
        sys.exit("APIFY_API_TOKEN is missing. Set it in .env")
    return token


def find_hd_url(value: Any) -> str | None:
    """Return the first nested `browser_native_hd_url` in `value`."""
    if isinstance(value, dict):
        url = value.get("browser_native_hd_url")
        if isinstance(url, str) and url.startswith("http"):
            return url
        for nested in value.values():
            found = find_hd_url(nested)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_hd_url(item)
            if found:
                return found
    return None


def download_video(video_url: str, dest: Path) -> None:
    """GET `video_url` and write the bytes to `dest`."""
    request = urllib.request.Request(
        video_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        dest.write_bytes(response.read())


def main() -> None:
    load_env(ROOT / ".env")
    client = ApifyClient(require_token())
    run = client.actor(ACTOR_ID).call(
        run_input={
            "startUrls": [{"url": REEL_URL}],
            "resultsLimit": 1,
            "captionText": False,
        }
    )
    if not run:
        sys.exit("Apify actor run failed.")

    dataset_id = (
        run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    )
    items = list(client.dataset(dataset_id).iterate_items())
    if not items:
        sys.exit("Actor returned no posts.")

    fields = items[0]
    video_url = find_hd_url(fields)
    if not video_url:
        sys.exit("No browser_native_hd_url in actor output.")

    download_video(video_url, OUTPUT_PATH)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
