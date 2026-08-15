"""Runs the AI Farm script.

The script is a polling loop over fixed directories inside the AI Farm root: it
waits for ``from_user/data`` to appear with an ``info.csv`` inside, runs
``<product id>.py``, writes the output to ``to_user`` and then removes
``from_user/data``.

So a run means: stage the dataset plus ``info.csv``, start the script, wait for
the hand-off to complete, stop the script and zip up ``to_user``. Because those
directories are global, only one run may be in flight at a time - the Celery job
enforces that with a lock.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import time
from pathlib import Path

from aifarm.products import Product
from otis.config import AIFarmSettings, get_settings
from otis.exceptions import AIFarmError
from otis.logging import get_logger

logger = get_logger(__name__)

PYTHON_EXECUTABLE = "python3"
#: How often the result directory is polled while the script runs.
POLL_INTERVAL_SECONDS = 2.0
#: Give up on a run that produced no result within this many seconds.
TIMEOUT_SECONDS = 7200.0

_ERROR_STATUS_FILE = "Error_Status.csv"
_LOG_TAIL_LINES = 40


class AIFarmService:
    """Hands a dataset to the AI Farm script and collects its result."""

    def __init__(self, settings: AIFarmSettings | None = None) -> None:
        self._settings = settings or get_settings().aifarm

    def run(
        self,
        product: Product,
        model_size: str,
        dataset_dir: Path,
        workdir: Path,
    ) -> Path:
        """Run ``product`` over ``dataset_dir`` and return a result zip in ``workdir``.

        Raises :class:`AIFarmError` if the script produces no usable result.
        """
        settings = self._settings
        if not settings.script_path.is_file():
            raise AIFarmError(f"AI Farm script not found at {settings.script_path}")

        logger.info(
            "AI Farm run: product=%s (%s) size=%s root=%s",
            int(product),
            product.label,
            model_size,
            settings.root,
        )
        self._clean_directories()
        try:
            self._stage_input(product, model_size, dataset_dir)
            log_path = self._run_script(workdir)
            self._raise_on_error_status(log_path)
            return self._archive_result(workdir)
        finally:
            self._clean_directories()

    def _stage_input(self, product: Product, model_size: str, dataset_dir: Path) -> None:
        """Copy the dataset into ``from_user/data``, then write ``info.csv``.

        ``info.csv`` goes last: the script treats a data directory without it as
        a failed upload.
        """
        settings = self._settings
        settings.data_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dataset_dir, settings.data_dir)

        content = self._render_info_csv(product, model_size)
        settings.info_csv_path.write_text(content, encoding="utf-8")
        logger.info("Staged dataset in %s with info.csv:\n%s", settings.data_dir, content.strip())

    def _render_info_csv(self, product: Product, model_size: str) -> str:
        try:
            content = self._settings.info_csv_template.format(
                product_id=int(product),
                product_label=product.label,
                model_size=model_size,
            )
        except (KeyError, IndexError) as exc:
            raise AIFarmError(
                f"Invalid AIFARM_INFO_CSV_TEMPLATE: unknown placeholder {exc}"
            ) from exc
        return content if content.endswith("\n") else content + "\n"

    def _run_script(self, workdir: Path) -> Path:
        """Start the script, wait for the result, then stop it. Returns its log."""
        settings = self._settings
        workdir.mkdir(parents=True, exist_ok=True)
        log_path = workdir / "aifarm_script.log"

        logger.info("Starting AI Farm script %s", settings.script_path)
        with log_path.open("wb") as log_file:
            process = subprocess.Popen(  # noqa: S603 - script path comes from our own config
                # -u: the script is stopped rather than exiting, so its output
                # must not sit in a buffer we never get to flush.
                [PYTHON_EXECUTABLE, "-u", str(settings.script_path)],
                cwd=settings.root,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            try:
                self._wait_for_result(process, log_path)
            finally:
                self._stop(process)
        return log_path

    def _wait_for_result(self, process: subprocess.Popen[bytes], log_path: Path) -> None:
        """Block until the script hands the result over, or fail trying.

        The hand-off is done when ``to_user`` exists and the script has removed
        ``from_user/data``.
        """
        settings = self._settings
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while True:
            if settings.to_user_dir.exists() and not settings.data_dir.exists():
                logger.info("AI Farm script produced a result in %s", settings.to_user_dir)
                return
            if process.poll() is not None:
                raise AIFarmError(
                    f"AI Farm script exited with code {process.returncode} "
                    f"before producing a result. Log tail:\n{_tail(log_path)}"
                )
            if time.monotonic() > deadline:
                raise AIFarmError(
                    f"AI Farm script produced no result within "
                    f"{TIMEOUT_SECONDS:.0f}s. Log tail:\n{_tail(log_path)}"
                )
            time.sleep(POLL_INTERVAL_SECONDS)

    def _stop(self, process: subprocess.Popen[bytes]) -> None:
        """Stop the script; it loops forever and never exits on its own."""
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("AI Farm script did not terminate, killing it")
            process.kill()
            process.wait(timeout=10)
        logger.info("AI Farm script stopped")

    def _raise_on_error_status(self, log_path: Path) -> None:
        """Turn the script's ``Error_Status.csv`` hand-off into an exception."""
        error_file = self._settings.to_user_dir / _ERROR_STATUS_FILE
        if not error_file.exists():
            return
        message = _read_error_status(error_file)
        raise AIFarmError(f"AI Farm reported an error: {message}\nLog tail:\n{_tail(log_path)}")

    def _archive_result(self, workdir: Path) -> Path:
        to_user = self._settings.to_user_dir
        if not any(to_user.iterdir()):
            raise AIFarmError(f"AI Farm result directory {to_user} is empty")

        base = workdir / "aifarm_result"
        archive = Path(shutil.make_archive(str(base), "zip", root_dir=to_user))
        logger.info("Archived AI Farm result to %s (%s bytes)", archive, archive.stat().st_size)
        return archive

    def _clean_directories(self) -> None:
        """Remove ``from_user`` and ``to_user`` so every run starts from scratch."""
        for directory in (self._settings.from_user_dir, self._settings.to_user_dir):
            if directory.exists():
                logger.info("Removing %s", directory)
                shutil.rmtree(directory, ignore_errors=True)


def _read_error_status(error_file: Path) -> str:
    """Read ``Error_Status.csv`` back into a sentence.

    The script writes the message with ``csv.writerow(str)``, which puts every
    character in its own column, so a row of single characters is re-joined as
    one word.
    """
    text = error_file.read_text(encoding="utf-8", errors="replace")
    messages = []
    for row in csv.reader(text.splitlines()):
        if not row:
            continue
        separator = "" if all(len(cell) <= 1 for cell in row) else ", "
        messages.append(separator.join(row))
    return " ".join(messages).strip() or text.strip()


def _tail(log_path: Path, lines: int = _LOG_TAIL_LINES) -> str:
    """Last few lines of the script log, for error messages."""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "<script log unavailable>"
    return "\n".join(content.splitlines()[-lines:]) or "<empty>"
