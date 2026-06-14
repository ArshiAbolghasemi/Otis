"""Data-access for submissions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from otis.models import Submission, SubmissionStatus


class SubmissionRepository:
    """CRUD operations for :class:`Submission` records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, *, email: str, upload_link: str, model_size: str, model_type: str
    ) -> Submission:
        submission = Submission(
            email=email,
            upload_link=upload_link,
            model_size=model_size,
            model_type=model_type,
            status=SubmissionStatus.PENDING,
        )
        self._session.add(submission)
        self._session.commit()
        self._session.refresh(submission)
        return submission

    def get(self, submission_id: int) -> Submission | None:
        return self._session.get(Submission, submission_id)

    def set_status(
        self,
        submission_id: int,
        status: SubmissionStatus,
        *,
        error: str | None = None,
    ) -> None:
        submission = self._session.get(Submission, submission_id)
        if submission is None:
            return
        submission.status = status
        submission.error = error
        self._session.commit()
