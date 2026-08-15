"""Dataset upload HTTP endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from data.dependencies import get_data_service
from data.schemas import UploadedData
from data.service import DataService
from otis.exceptions import InvalidUploadError, StorageError
from otis.logging import get_logger

logger = get_logger(__name__)

#: Datasets larger than this are refused up front, on the Content-Length header.
MAX_UPLOAD_BYTES = 2 * 1024**3

router = APIRouter(tags=["data"])


@router.post(
    "/data",
    response_model=UploadedData,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a dataset archive",
    description=(
        "Stores a `.zip` dataset in object storage and returns the link to it. "
        "That link is what `POST /v1/model` expects as `upload_link`."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "The file is not a zip archive"},
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "The file is too large"},
    },
)
def upload_data(
    request: Request,
    file: UploadFile = File(..., description="The dataset, as a .zip archive"),
    service: DataService = Depends(get_data_service),
) -> UploadedData:
    """Store an uploaded dataset and return its link.

    Defined as a sync endpoint so FastAPI runs the blocking upload in a
    threadpool instead of on the event loop.
    """
    _reject_oversized(request)
    logger.info("Received dataset %r (%s)", file.filename, file.content_type)
    try:
        return service.store(file.filename, file.file)
    except InvalidUploadError as exc:
        logger.info("Rejected dataset %r: %s", file.filename, exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except StorageError as exc:
        logger.exception("Upload of %r failed", file.filename)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not store the file, please try again",
        ) from exc


def _reject_oversized(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The dataset must be smaller than {MAX_UPLOAD_BYTES // 1024**3} GB",
        )
