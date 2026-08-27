"""Fetch a thumbnail URL, convert it to JPEG, and upload it to Storage."""

from __future__ import annotations

import urllib.request
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field
from supabase import StorageException

from recipe_kitchen.core.config import get_settings
from recipe_kitchen.db.supabase import get_supabase_admin

JPEG_QUALITY = 85
TEST1_THUMBNAIL_URL = ""


class StoredThumbnail(BaseModel):
    bucket: str = Field(min_length=1)
    path: str = Field(min_length=1)


def _storage():
    """Return `(client, bucket_name)` for the configured Storage bucket."""
    settings = get_settings()
    bucket = settings.supabase_storage_bucket.strip()
    if not bucket:
        raise RuntimeError("SUPABASE_STORAGE_BUCKET is missing")
    return get_supabase_admin().storage.from_(bucket), bucket


def _fetch(url: str, *, timeout: float) -> bytes:
    """GET `url` and return the response body."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Download was empty.")
    return data


def _is_jpeg(data: bytes) -> bool:
    """Return True when `data` starts with a JPEG SOI marker."""
    return data[:2] == b"\xff\xd8"


def _to_jpeg(data: bytes) -> bytes:
    """Decode `data` and re-encode it as RGB JPEG."""
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise RuntimeError("Thumbnail is not a valid image.") from exc
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


def download_thumbnail(thumbnail_url: str, object_path: str) -> StoredThumbnail:
    """GET `thumbnail_url`, convert to JPEG if needed, and upload it to Storage."""
    storage, bucket = _storage()
    path = object_path.lstrip("/")
    if not path:
        raise RuntimeError("Thumbnail object path is empty.")

    data = _fetch(thumbnail_url, timeout=30)
    if not _is_jpeg(data):
        data = _to_jpeg(data)

    try:
        storage.upload(
            path,
            data,
            file_options={
                "content-type": "image/jpeg",
                "upsert": "false",
            },
        )
    except StorageException as exc:
        raise RuntimeError(f"Failed to upload thumbnail: {exc}") from exc
    return StoredThumbnail(bucket=bucket, path=path)


def delete_thumbnail(object_path: str) -> None:
    """Remove `object_path` from the Storage bucket."""
    storage, _bucket = _storage()
    path = object_path.lstrip("/")
    if not path:
        raise RuntimeError("Thumbnail object path is empty.")
    try:
        storage.remove([path])
    except StorageException as exc:
        raise RuntimeError(f"Failed to delete thumbnail: {exc}") from exc


def main() -> None:
    """Upload the test1 Facebook CDN thumbnail, then delete it."""
    if not TEST1_THUMBNAIL_URL:
        raise RuntimeError("Set TEST1_THUMBNAIL_URL to a current Facebook thumbnail CDN link")
    stored = download_thumbnail(TEST1_THUMBNAIL_URL, "test1/thumbnail.jpg")
    try:
        print(stored.model_dump_json(indent=2))
    finally:
        delete_thumbnail(stored.path)


if __name__ == "__main__":
    main()
