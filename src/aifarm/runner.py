"""AI Farm runner: orchestrates download, unzip and the AI Farm service."""

from __future__ import annotations

import tempfile
from pathlib import Path

from aifarm.products import Product
from aifarm.service import AIFarmService
from infrastructure.minio.client import MinioClient
from otis.logging import get_logger
from util.file import unzip
from util.http import download_zip

logger = get_logger(__name__)


class AIFarmRunner:
    """Turns an upload link into an AI Farm result archive."""

    def __init__(
        self,
        service: AIFarmService | None = None,
        storage: MinioClient | None = None,
    ) -> None:
        self._service = service or AIFarmService()
        self._storage = storage or MinioClient()

    def run(
        self,
        upload_link: str,
        product: Product,
        model_size: str,
        result_dir: Path,
    ) -> Path:
        """Download the archive at ``upload_link``, extract it and run AI Farm.

        The downloaded archive and extracted files live in a temporary
        directory that is removed as soon as AI Farm has consumed them. The
        result is written into ``result_dir``, which is left for the caller
        to manage. Raises ``DownloadError`` / ``UnzipError`` on invalid input
        and ``AIFarmError`` when AI Farm produces no result.
        """
        logger.info("AI Farm run started for link %s", upload_link)

        with tempfile.TemporaryDirectory(prefix="otis-input-") as tmp:
            tmp_path = Path(tmp)
            archive = self._fetch(upload_link, tmp_path / "upload.zip")
            dataset_dir = unzip(archive, tmp_path / "extracted")
            result = self._service.run(
                product=product,
                model_size=model_size,
                dataset_dir=dataset_dir,
                workdir=result_dir,
            )

        logger.info("AI Farm run finished, result at %s", result)
        return result

    def _fetch(self, upload_link: str, destination: Path) -> Path:
        """Get the upload, from object storage when the link is one of ours.

        Datasets uploaded through the form live in our own bucket, so they are
        fetched with credentials - the link the user pasted may have expired by
        the time the job runs. Any other link is downloaded over HTTP.
        """
        key = self._storage.key_for_url(upload_link)
        if key is None:
            return download_zip(upload_link, destination)

        logger.info("Upload link points at our own storage, fetching %s", key)
        return self._storage.download(key, destination)
