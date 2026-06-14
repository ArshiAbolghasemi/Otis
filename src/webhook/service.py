"""Webhook application logic: persist the submission and enqueue a job."""

from __future__ import annotations

from typing import cast

from celery import Task
from sqlalchemy.orm import Session

from aifarm.job import process_submission
from otis.logging import get_logger
from otis.models import Submission
from otis.repository import SubmissionRepository
from webhook.schemas import WebhookPayload

logger = get_logger(__name__)


class WebhookService:
    """Stores incoming submissions and dispatches them for processing."""

    def __init__(self, session: Session) -> None:
        self._repository = SubmissionRepository(session)

    def submit(self, payload: WebhookPayload) -> Submission:
        """Persist the payload, then enqueue a Celery job by submission id."""
        submission = self._repository.create(
            email=str(payload.email),
            upload_link=payload.upload_link,
            model_size=payload.model_size.value,
            model_type=payload.model_type.value,
        )
        logger.info("Stored submission %s for %s", submission.id, submission.email)

        task = cast(Task, process_submission)
        task.delay(submission.id)
        logger.info("Enqueued processing job for submission %s", submission.id)
        return submission
