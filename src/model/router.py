"""Model request HTTP endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from model.dependencies import get_model_service
from model.schemas import ModelRequest, ModelResponse
from model.service import ModelService
from otis.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["model"])


@router.post(
    "/model",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a model for an uploaded dataset",
    description=(
        "Stores the request and enqueues a Celery job that fetches the dataset "
        "at `upload_link`, runs AI Farm and emails the result to `email`."
    ),
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid request"},
    },
)
def request_model(
    request: ModelRequest,
    service: ModelService = Depends(get_model_service),
) -> ModelResponse:
    """Store a model request and enqueue it for processing."""
    logger.info("Received model request for %s", request.email)
    submission = service.submit(request)
    return ModelResponse(id=submission.id)
