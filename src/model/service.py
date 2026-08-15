"""Model application logic: persist the submission and enqueue a job."""

from __future__ import annotations

from typing import cast

from celery import Task
from sqlalchemy.orm import Session

from aifarm.job import process_submission
from model.schemas import ModelRequest
from otis.logging import get_logger
from otis.models import Submission
from otis.repository import SubmissionRepository

logger = get_logger(__name__)


class ModelService:
    """Stores incoming requests and dispatches them for processing."""

    def __init__(self, session: Session) -> None:
        self._repository = SubmissionRepository(session)

    def submit(self, request: ModelRequest) -> Submission:
        """Persist the request, then enqueue a Celery job by submission id."""
        submission = self._repository.create(
            email=str(request.email),
            upload_link=request.upload_link,
            model_size=request.model_size.value,
            product_id=int(request.product_id),
        )
        logger.info(
            "Stored submission %s for %s (product %s)",
            submission.id,
            submission.email,
            request.product_id.label,
        )

        task = cast(Task, process_submission)
        task.delay(submission.id)
        logger.info("Enqueued processing job for submission %s", submission.id)
        return submission
