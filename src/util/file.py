"""File (zip archive) utilities."""

from __future__ import annotations

import zipfile
from pathlib import Path

from otis.exceptions import UnzipError
from otis.logging import get_logger

logger = get_logger(__name__)


def unzip(archive: Path, destination: Path) -> Path:
    """Extract ``archive`` into ``destination`` and return that directory.

    The whole tree is kept as uploaded - AI Farm products range from tabular
    files to image folders, so the layout inside the archive is the user's to
    decide. Raises :class:`UnzipError` if the archive is invalid, escapes the
    destination, or holds no files.
    """
    if not zipfile.is_zipfile(archive):
        raise UnzipError(f"{archive.name} is not a valid zip archive")

    destination.mkdir(parents=True, exist_ok=True)
    resolved_destination = destination.resolve()
    logger.info("Extracting %s to %s", archive, destination)
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            target = (resolved_destination / member).resolve()
            if not target.is_relative_to(resolved_destination):
                raise UnzipError(f"Archive entry {member!r} escapes the extraction directory")
        zf.extractall(destination)

    files = [path for path in destination.rglob("*") if path.is_file()]
    if not files:
        raise UnzipError("Archive must contain at least one file")

    logger.info("Extracted %d file(s) into %s", len(files), destination)
    return destination
