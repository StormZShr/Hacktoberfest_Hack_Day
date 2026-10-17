"""Saving and serving uploaded ZIPs. Size and type checks are plain code, never AI."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

import config

CHUNK_BYTES = 1024 * 1024


def _storage_dir() -> Path:
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return config.STORAGE_DIR


async def save_zip(project_id: int, upload: UploadFile) -> tuple[str, int]:
    """Stream the upload to disk under a random name. Returns (file name, bytes)."""
    original = (upload.filename or "").strip()
    if not original.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="upload a .zip file")

    destination = _storage_dir() / f"project{project_id}_{uuid4().hex}.zip"
    size = 0
    try:
        with destination.open("wb") as handle:
            while True:
                chunk = await upload.read(CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"that ZIP is larger than {config.MAX_UPLOAD_MB} MB",
                    )
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="that ZIP is empty")
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="could not save the ZIP") from exc

    return destination.name, size


def zip_path(file_name: str) -> Path:
    """Resolve a stored file name inside the storage dir, or 404."""
    candidate = (_storage_dir() / Path(file_name).name).resolve()
    if candidate.parent != config.STORAGE_DIR.resolve() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return candidate


def delete_zip(file_name: str | None) -> None:
    """Remove a replaced upload. Never raises: a missing file is not an error."""
    if not file_name:
        return
    try:
        zip_path(file_name).unlink(missing_ok=True)
    except HTTPException:
        return
