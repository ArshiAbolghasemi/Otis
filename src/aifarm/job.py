"""Celery job that processes a submission end to end."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from celery import Task

from aifarm.products import Product
from aifarm.runner import AIFarmRunner
from infrastructure.celery.app import celery_app
from infrastructure.db.session import session_scope
from infrastructure.mail.sender import MailSender
from infrastructure.minio.client import MinioClient
from infrastructure.redis.lock import try_lock
from otis.config import Settings, get_settings
from otis.logging import get_logger
from otis.models import SubmissionStatus
from otis.repository import SubmissionRepository

logger = get_logger(__name__)

#: Only one AI Farm run at a time: the run holds this Redis lock. The TTL caps
#: how long a crashed worker keeps it, so it must outlast the longest run.
LOCK_KEY = "otis:aifarm:lock"
LOCK_TTL_SECONDS = 7800
#: How long a job waits before re-queueing itself when the lock is taken.
BUSY_RETRY_SECONDS = 30


@celery_app.task(bind=True, name="otis.process_submission", max_retries=None)
def process_submission(self: Task, submission_id: int) -> None:
    """Download, process and email the result for a stored submission.

    AI Farm runs one submission at a time: if another submission holds the lock
    this job re-queues itself and lets the worker move on. On any failure the
    submission is marked FAILED, the reason is logged, and an error email is
    sent to the submitter.
    """
    logger.info("Job started for submission %s", submission_id)
    settings = get_settings()

    with try_lock(settings.celery.broker_url, LOCK_KEY, LOCK_TTL_SECONDS) as acquired:
        if not acquired:
            logger.info(
                "AI Farm is busy; re-queueing submission %s in %ss",
                submission_id,
                BUSY_RETRY_SECONDS,
            )
            raise self.retry(countdown=BUSY_RETRY_SECONDS)

        _process(submission_id)


def _process(submission_id: int) -> None:
    """Run the pipeline for one submission, reporting the outcome to the user."""
    settings = get_settings()
    mailer = MailSender(settings.mail)

    with session_scope() as session:
        repo = SubmissionRepository(session)
        submission = repo.get(submission_id)
        if submission is None:
            logger.error("Submission %s not found; aborting job", submission_id)
            return

        email = submission.email
        upload_link = submission.upload_link
        product_id = submission.product_id
        model_size = submission.model_size

        repo.set_status(submission_id, SubmissionStatus.PROCESSING)
        logger.info("Submission %s set to PROCESSING", submission_id)

        try:
            with tempfile.TemporaryDirectory(prefix="otis-result-") as tmp:
                logger.info("Processing submission %s, result dir %s", submission_id, tmp)
                result = AIFarmRunner().run(
                    upload_link=upload_link,
                    product=Product(product_id),
                    model_size=model_size,
                    result_dir=Path(tmp),
                )

                # The archive is too big to attach, so it is stored and linked.
                download_link = MinioClient().upload(result, _result_key(submission_id, result))

            logger.info("Emailing result link for submission %s to %s", submission_id, email)
            mailer.send(
                to=email,
                subject=settings.mail.result_subject,
                body=_result_body(settings, download_link),
            )

            repo.set_status(submission_id, SubmissionStatus.SUCCESS)
            logger.info("Submission %s completed successfully", submission_id)

        except Exception as exc:  # noqa: BLE001 - we report any failure back to the user
            logger.exception("Submission %s failed: %s", submission_id, exc)
            repo.set_status(submission_id, SubmissionStatus.FAILED, error=str(exc))
            _notify_failure(mailer, settings, email, submission_id, exc)


def _result_key(submission_id: int, result: Path) -> str:
    """Object key for a result: grouped per submission, unique per attempt."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"results/{submission_id}/{stamp}-{result.name}"


def _result_body(settings: Settings, download_link: str) -> str:
    """Fill the download link into the configured result body."""
    body = settings.mail.result_body
    if "{download_link}" not in body:
        return f"{body}\n{download_link}"
    return body.format(
        download_link=download_link,
        expires_in=_humanise(settings.minio.link_expiry_seconds),
    )


def _humanise(seconds: int) -> str:
    """Turn a link lifetime into something readable in an email."""
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size:
            amount = seconds // size
            return f"{amount} {unit}{'s' if amount > 1 else ''}"
    return f"{seconds} seconds"


def _notify_failure(mailer, settings, email, submission_id, exc) -> None:
    """Best-effort error email; never raises out of the job."""
    try:
        mailer.send(
            to=email,
            subject=settings.mail.error_subject,
            body=f"{settings.mail.error_body}{exc}",
        )
        logger.info("Error email sent for submission %s", submission_id)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send error email for submission %s", submission_id)
