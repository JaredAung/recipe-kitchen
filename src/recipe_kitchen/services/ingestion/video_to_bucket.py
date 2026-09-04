"""Fetch a video URL and upload it to Supabase Storage."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from pydantic import BaseModel, Field
from storage3.utils import StorageException

from recipe_kitchen.core.config import get_settings
from recipe_kitchen.db.supabase import get_supabase_admin

TEST1_VIDEO_URL = (
    "https://video-atl3-2.xx.fbcdn.net/o1/v/t2/f2/m367/"
    "AQPgzH7ecUvh1j6h24YVWxPmsKigBaFqvZP0mhMuni4dmiQ32wM66AYrl_3I8u14"
    "YJkC9m2eJY_FAgmg-sVsgwllzPOxSrzMxGcNfwvZmQ.mp4"
    "?_nc_cat=101&_nc_sid=8bf8fe&_nc_ht=video-atl3-2.xx.fbcdn.net"
    "&_nc_ohc=R6WtabCsKG8Q7kNvwEZBUc_"
    "&efg=eyJ2ZW5jb2RlX3RhZyI6Inhwdl9wcm9ncmVzc2l2ZS5GQUNFQk9PSy4uQzMuMzYwLnByb2dyZXNzaXZlX2gyNjQtYmFzaWMtZ2VuMl8zNjBwIiwieHB2X2Fzc2V0X2lkIjoxNDQ3NTMwODQzNzc3MzU2LCJhc3NldF9hZ2VfZGF5cyI6NTUsInZpX3VzZWNhc2VfaWQiOjEwMDk5LCJkdXJhdGlvbl9zIjo0MCwidXJsZ2VuX3NvdXJjZSI6Ind3dyJ9"
    "&ccb=17-1&_nc_gid=Sb3XB0wAmNgQw2HK8rR0wA&_nc_ss=73289&_nc_zt=28"
    "&oh=00_AQFdD5OWfTtIhaeOYUt693nMNH2XbEUKJzrXjCiJQa5g3A&oe=6A9645BD"
    "&bitrate=465397&tag=progressive_h264-basic-gen2_360p"
)


class StoredVideo(BaseModel):
    bucket: str = Field(min_length=1)
    path: str = Field(min_length=1)


def _storage():
    """Return `(client, bucket_name)` for the configured Storage bucket."""
    settings = get_settings()
    bucket = settings.supabase_storage_bucket.strip()
    if not bucket:
        raise RuntimeError("SUPABASE_STORAGE_BUCKET is missing")
    return get_supabase_admin().storage.from_(bucket), bucket


def _fetch(url: str, *, timeout: float) -> tuple[bytes, str]:
    """GET `url` and return `(body, content_type)`."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
        content_type = response.headers.get_content_type() or "application/octet-stream"
    if not data:
        raise RuntimeError("Download was empty.")
    return data, content_type


def _upload_bytes(path: str, data: bytes, content_type: str) -> StoredVideo:
    """Upload `data` to `path` in the Storage bucket."""
    storage, bucket = _storage()
    object_path = path.lstrip("/")
    if not object_path:
        raise RuntimeError("Video object path is empty.")
    if not data:
        raise RuntimeError("Upload was empty.")
    try:
        storage.upload(
            object_path,
            data,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
    except StorageException as exc:
        raise RuntimeError(f"Failed to upload video: {exc}") from exc
    return StoredVideo(bucket=bucket, path=object_path)


def download_video(video_url: str, object_path: str) -> StoredVideo:
    """GET `video_url` and upload it to the Storage bucket."""
    data, content_type = _fetch(video_url, timeout=120)
    if content_type == "application/octet-stream":
        content_type = "video/mp4"
    return _upload_bytes(object_path, data, content_type)


def upload_local_video(video_path: Path, object_path: str) -> StoredVideo:
    """Upload a local video file to the Storage bucket."""
    suffix = video_path.suffix.lower()
    content_type = "video/quicktime" if suffix == ".mov" else "video/mp4"
    return _upload_bytes(object_path, video_path.read_bytes(), content_type)


def fetch_stored_video(object_path: str) -> bytes:
    """Download a stored video object as bytes."""
    storage, _bucket = _storage()
    path = object_path.lstrip("/")
    if not path:
        raise RuntimeError("Video object path is empty.")
    try:
        data = storage.download(path)
    except StorageException as exc:
        raise RuntimeError(f"Failed to download video: {exc}") from exc
    if not data:
        raise RuntimeError("Stored video was empty.")
    return data


def delete_video(object_path: str) -> None:
    """Remove `object_path` from the Storage bucket."""
    storage, _bucket = _storage()
    path = object_path.lstrip("/")
    if not path:
        raise RuntimeError("Video object path is empty.")
    try:
        storage.remove([path])
    except StorageException as exc:
        raise RuntimeError(f"Failed to delete video: {exc}") from exc


def main() -> None:
    """Upload the test1 Facebook CDN video, then delete it."""
    stored = download_video(TEST1_VIDEO_URL, "test1/video.mp4")
    try:
        print(stored.model_dump_json(indent=2))
    finally:
        delete_video(stored.path)


if __name__ == "__main__":
    main()
