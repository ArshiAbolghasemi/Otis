"""File (zip archive) utilities."""

from __future__ import annotations

import zipfile
from pathlib import Path

from otis.exceptions import UnzipError
from otis.logging import get_logger

logger = get_logger(__name__)

_ALLOWED_SUFFIXES = {".xlsx", ".csv"}


def unzip(archive: Path, destination: Path) -> list[Path]:
    """Extract ``archive`` into ``destination`` and return data files found.

    Only ``.xlsx`` and ``.csv`` files are considered usable. Raises
    :class:`UnzipError` if the archive is invalid or holds no such file.
    """
    if not zipfile.is_zipfile(archive):
        raise UnzipError(f"{archive.name} is not a valid zip archive")

    destination.mkdir(parents=True, exist_ok=True)
    logger.info("Extracting %s to %s", archive, destination)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(destination)

    data_files = [
        path
        for path in destination.rglob("*")
        if path.is_file() and path.suffix.lower() in _ALLOWED_SUFFIXES
    ]
    if not data_files:
        raise UnzipError("Archive must contain at least one .xlsx or .csv file")

    logger.info("Extracted %d data file(s): %s", len(data_files), [p.name for p in data_files])
    return data_files
