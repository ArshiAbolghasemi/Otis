"""Webhook HTTP endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from otis.logging import get_logger
from webhook.dependencies import get_webhook_service, verify_api_key
from webhook.schemas import WebhookPayload, WebhookResponse
from webhook.service import WebhookService

logger = get_logger(__name__)

router = APIRouter(tags=["webhook"])


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
    summary="Receive a Porsline webhook submission",
    description=(
        "Stores the submission in the database and enqueues a Celery job that "
        "downloads the upload, runs AI Farm and emails the result to `email`. "
        "Requires a valid `x-api-key` header."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid x-api-key header"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid payload"},
    },
)
def receive_webhook(
    payload: WebhookPayload,
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookResponse:
    """Store an incoming submission and enqueue it for processing."""
    logger.info("Received webhook for %s", payload.email)
    submission = service.submit(payload)
    return WebhookResponse(id=submission.id)
