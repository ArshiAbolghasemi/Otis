"""AI Farm service.

The real modelling is not implemented yet. :meth:`execute` ignores the input
dataset and returns a sample result zip so the rest of the pipeline can run end
to end.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from otis.logging import get_logger

logger = get_logger(__name__)


class AIFarmService:
    """Placeholder AI Farm computation."""

    def execute(self, dataset_files: list[Path], workdir: Path) -> Path:
        """Run the model over ``dataset_files`` and return a result zip.

        Not implemented yet: returns a sample archive regardless of input.
        """
        logger.info("Running AI Farm over %d file(s)", len(dataset_files))
        workdir.mkdir(parents=True, exist_ok=True)
        result = workdir / "aifarm_result.zip"
        with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "result.txt",
                "This is a sample AI Farm result. Real model execution is not implemented yet.\n",
            )
        logger.info("AI Farm produced result archive at %s", result)
        return result
