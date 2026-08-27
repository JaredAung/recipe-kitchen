"""Extract fields from raw Facebook scrape data."""

from __future__ import annotations

import re

from recipe_kitchen.schemas.facebook import FacebookMedia

_PATH_TOKEN = re.compile(r"([^.\[\]]+)(?:\[(\d+)\])?")


def _at(data: dict, path: str) -> object:
    """Return the value at a dotted JSON path, including `attachments[0]`."""
    current: object = data
    for match in _PATH_TOKEN.finditer(path):
        key, index = match.group(1), match.group(2)
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if index is None:
            continue
        if not isinstance(current, list):
            return None
        position = int(index)
        if position >= len(current):
            return None
        current = current[position]
    return current


def _item(data: dict | list[dict]) -> dict:
    """Return the first scrape item from a dataset list or a single dict."""
    if isinstance(data, list):
        if not data or not isinstance(data[0], dict):
            raise RuntimeError("Actor returned no posts.")
        return data[0]
    return data


def extract_facebook_media(data: dict | list[dict]) -> FacebookMedia:
    """Pull recipe-relevant media fields from raw Facebook scrape JSON."""
    item = _item(data)
    video = "short_form_video_context.playback_video"
    delivery = f"{video}.videoDeliveryLegacyFields"
    return FacebookMedia.model_validate(
        {
            "video_id": _at(item, "facebookId"),
            "source_url": _at(item, "facebookUrl"),
            "caption": _at(item, "message.text"),
            "hd_url": _at(item, f"{delivery}.browser_native_hd_url"),
            "sd_url": _at(item, f"{delivery}.browser_native_sd_url"),
            "thumbnail_url": _at(item, f"{video}.thumbnailImage.uri"),
            "duration": _at(item, f"{video}.length_in_second"),
            "width": _at(item, f"{video}.width"),
            "height": _at(item, f"{video}.height"),
            "subtitles_url": _at(item, f"{video}.captions_url"),
            "audio_available": _at(item, f"{video}.audio_availability"),
            "creator_name": _at(item, "short_form_video_context.video_owner.name"),
            "audio_title": _at(item, "short_form_video_context.track_title"),
        }
    )
