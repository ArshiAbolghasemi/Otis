"""Dataset application logic: validate the archive and store it."""

from __future__ import annotations

import re
from typing import BinaryIO
from uuid import uuid4

from data.schemas import UploadedData
from infrastructure.minio.client import MinioClient
from otis.exceptions import InvalidUploadError
from otis.logging import get_logger

logger = get_logger(__name__)

ZIP_CONTENT_TYPE = "application/zip"
#: Local zip file header - the first bytes of any non-empty archive.
_ZIP_MAGIC = b"PK\x03\x04"
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_FALLBACK_NAME = "dataset.zip"


class DataService:
    """Stores a user's dataset archive in object storage."""

    def __init__(self, storage: MinioClient | None = None) -> None:
        self._storage = storage or MinioClient()

    def store(self, filename: str | None, stream: BinaryIO) -> UploadedData:
        """Validate the archive and upload it under its own key.

        Raises :class:`InvalidUploadError` if the file is not a zip archive.
        """
        name = _safe_name(filename)
        _ensure_zip(name, stream)

        key = f"uploads/{uuid4().hex}/{name}"
        logger.info("Storing dataset %s as %s", name, key)
        link = self._storage.upload_stream(stream, key, ZIP_CONTENT_TYPE)
        return UploadedData(filename=name, key=key, link=link)


def _safe_name(filename: str | None) -> str:
    """Strip any directory and unusual characters from the browser's filename."""
    base = (filename or "").replace("\\", "/").split("/")[-1].strip()
    cleaned = _UNSAFE_CHARS.sub("_", base).lstrip(".")
    return cleaned or _FALLBACK_NAME


def _ensure_zip(name: str, stream: BinaryIO) -> None:
    """Reject anything that is not a zip, by extension and by magic bytes."""
    if not name.lower().endswith(".zip"):
        raise InvalidUploadError("Only .zip files are accepted")

    header = stream.read(len(_ZIP_MAGIC))
    stream.seek(0)
    if header != _ZIP_MAGIC:
        raise InvalidUploadError("The file is not a valid zip archive, or it is empty")
