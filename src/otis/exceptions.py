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
