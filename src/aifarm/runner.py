"""AI Farm runner: orchestrates download, unzip and the AI Farm service."""

from __future__ import annotations

import tempfile
from pathlib import Path

from aifarm.service import AIFarmService
from otis.logging import get_logger
from util.file import unzip
from util.http import download_zip

logger = get_logger(__name__)


class AIFarmRunner:
    """Turns an upload link into an AI Farm result archive."""

    def __init__(self, service: AIFarmService | None = None) -> None:
        self._service = service or AIFarmService()

    def run(self, upload_link: str, result_dir: Path) -> Path:
        """Download the archive at ``upload_link``, extract it and run AI Farm.

        The downloaded archive and extracted files live in a temporary
        directory that is removed as soon as AI Farm has consumed them. The
        result is written into ``result_dir``, which is left for the caller
        to manage. Raises ``DownloadError`` / ``UnzipError`` on invalid input.
        """
        logger.info("AI Farm run started for link %s", upload_link)

        with tempfile.TemporaryDirectory(prefix="otis-input-") as tmp:
            tmp_path = Path(tmp)
            archive = download_zip(upload_link, tmp_path / "upload.zip")
            dataset_files = unzip(archive, tmp_path / "extracted")
            result = self._service.execute(dataset_files, result_dir)

        logger.info("AI Farm run finished, result at %s", result)
        return result
