"""Application-wide exceptions for Otis."""

from __future__ import annotations


class OtisError(Exception):
    """Base class for all Otis errors."""


class DownloadError(OtisError):
    """Raised when a remote file cannot be downloaded or is not a zip archive."""


class UnzipError(OtisError):
    """Raised when an archive cannot be extracted or holds no usable data file."""


class SubmissionNotFoundError(OtisError):
    """Raised when a referenced submission does not exist."""


class AIFarmError(OtisError):
    """Raised when AI Farm fails to produce a result for a request."""


class StorageError(OtisError):
    """Raised when a file cannot be stored, fetched or linked in object storage."""


class InvalidUploadError(OtisError):
    """Raised when an uploaded file is not an acceptable dataset archive."""
