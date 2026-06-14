"""Celery job that processes a submission end to end."""

from __future__ import annotations

import tempfile
from pathlib import Path

from aifarm.runner import AIFarmRunner
from infrastructure.celery.app import celery_app
from infrastructure.db.session import session_scope
from infrastructure.mail.sender import MailSender
from otis.config import get_settings
from otis.logging import get_logger
from otis.models import SubmissionStatus
from otis.repository import SubmissionRepository

logger = get_logger(__name__)


@celery_app.task(name="otis.process_submission")
def process_submission(submission_id: int) -> None:
    """Download, process and email the result for a stored submission.

    On any failure the submission is marked FAILED, the reason is logged, and an
    error email is sent to the submitter.
    """
    logger.info("Job started for submission %s", submission_id)
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

        repo.set_status(submission_id, SubmissionStatus.PROCESSING)
        logger.info("Submission %s set to PROCESSING", submission_id)

        try:
            with tempfile.TemporaryDirectory(prefix="otis-result-") as tmp:
                logger.info("Processing submission %s, result dir %s", submission_id, tmp)
                result = AIFarmRunner().run(upload_link, Path(tmp))

                logger.info("Emailing result for submission %s to %s", submission_id, email)
                mailer.send(
                    to=email,
                    subject=settings.mail.result_subject,
                    body=settings.mail.result_body,
                    attachment=result,
                )

            repo.set_status(submission_id, SubmissionStatus.SUCCESS)
            logger.info("Submission %s completed successfully", submission_id)

        except Exception as exc:  # noqa: BLE001 - we report any failure back to the user
            logger.exception("Submission %s failed: %s", submission_id, exc)
            repo.set_status(submission_id, SubmissionStatus.FAILED, error=str(exc))
            _notify_failure(mailer, settings, email, submission_id, exc)


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
