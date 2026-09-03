"""Stream uploaded videos to disk with a size cap."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

MAX_UPLOAD_BYTES = 80 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


async def save_upload(file: UploadFile, *, suffix: str) -> Path:
    """Write `file` to a temp path. Rejects empty bodies and bodies over 80 MiB."""
    written = 0
    keep = False
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    try:
        while True:
            chunk = await file.read(CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="File too large.",
                )
            tmp.write(chunk)
        if written == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        keep = True
        return tmp_path
    finally:
        tmp.close()
        if not keep:
            tmp_path.unlink(missing_ok=True)
