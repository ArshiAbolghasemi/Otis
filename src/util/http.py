"""HTTP download utilities."""

from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from otis.exceptions import DownloadError
from otis.logging import get_logger

logger = get_logger(__name__)


def download_zip(url: str, destination: Path, *, timeout: float = 60.0) -> Path:
    """Download ``url`` to ``destination`` and ensure it is a zip archive.

    Raises :class:`DownloadError` if the request fails or the downloaded file
    is not a valid zip archive.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading file from %s", url)
    try:
        with (
            httpx.Client(timeout=timeout, follow_redirects=True) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            with destination.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
    except httpx.HTTPError as exc:
        raise DownloadError(f"Failed to download {url}: {exc}") from exc

    if not zipfile.is_zipfile(destination):
        raise DownloadError(f"Downloaded file from {url} is not a valid zip archive")

    logger.info("Downloaded %s bytes to %s", destination.stat().st_size, destination)
    return destination
