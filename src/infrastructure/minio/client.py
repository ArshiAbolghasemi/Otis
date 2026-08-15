"""Object storage client for any S3-compatible service (MinIO, Cloudflare R2).

Both ends of the pipeline pass through here: the user's dataset is uploaded from
the web form and fetched back by the worker, and the result archive - too big to
email - is uploaded and handed to the user as a pre-signed link.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from urllib.parse import unquote, urlparse

import boto3
from boto3.exceptions import Boto3Error
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from otis.config import MinioSettings, get_settings
from otis.exceptions import StorageError
from otis.logging import get_logger

logger = get_logger(__name__)

#: boto3 wraps transfer failures in its own error, outside the botocore tree.
_STORAGE_ERRORS = (Boto3Error, BotoCoreError, ClientError)
_CONTENT_TYPES = {".zip": "application/zip"}
_DEFAULT_CONTENT_TYPE = "application/octet-stream"


class MinioClient:
    """Uploads files and hands out pre-signed links to them."""

    def __init__(self, settings: MinioSettings | None = None) -> None:
        self._settings = settings or get_settings().minio
        self._client = boto3.client(
            "s3",
            endpoint_url=self._settings.endpoint_url,
            aws_access_key_id=self._settings.access_key,
            aws_secret_access_key=self._settings.secret_key,
            # R2 has no regions; "auto" is what it expects.
            region_name=self._settings.region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    def upload(self, file: Path, key: str) -> str:
        """Upload ``file`` under ``key`` and return a pre-signed download URL."""
        self._upload(file, key)
        return self._download_url(key)

    def upload_stream(self, fileobj: BinaryIO, key: str, content_type: str) -> str:
        """Stream ``fileobj`` under ``key`` and return a pre-signed download URL.

        Used for browser uploads, which never need to touch the API's disk.
        """
        bucket = self._settings.bucket
        logger.info("Streaming upload to %s/%s", bucket, key)
        try:
            self._client.upload_fileobj(
                Fileobj=fileobj,
                Bucket=bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type},
            )
        except _STORAGE_ERRORS as exc:
            raise StorageError(f"Failed to upload to {bucket}/{key}: {exc}") from exc
        logger.info("Uploaded %s/%s", bucket, key)
        return self._download_url(key)

    def download(self, key: str, destination: Path) -> Path:
        """Download ``key`` to ``destination``, which is returned."""
        bucket = self._settings.bucket
        destination.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading %s/%s to %s", bucket, key, destination)
        try:
            self._client.download_file(Bucket=bucket, Key=key, Filename=str(destination))
        except _STORAGE_ERRORS as exc:
            raise StorageError(f"Failed to download {bucket}/{key}: {exc}") from exc
        logger.info("Downloaded %s bytes from %s/%s", destination.stat().st_size, bucket, key)
        return destination

    def key_for_url(self, url: str) -> str | None:
        """The object key ``url`` points at, or ``None`` if it is not ours.

        Lets the worker fetch a link it handed out itself with credentials,
        rather than depending on the signature still being valid.
        """
        parsed = urlparse(url)
        endpoint = urlparse(self._settings.endpoint_url)
        if not parsed.netloc or not endpoint.netloc:
            return None

        bucket = self._settings.bucket
        path = unquote(parsed.path).lstrip("/")
        prefix = f"{bucket}/"
        if parsed.netloc == endpoint.netloc and path.startswith(prefix):
            return path[len(prefix) :] or None  # path style: /<bucket>/<key>
        if parsed.netloc == f"{bucket}.{endpoint.netloc}":
            return path or None  # virtual-hosted style: <bucket>.<host>/<key>
        return None

    def _upload(self, file: Path, key: str) -> None:
        bucket = self._settings.bucket
        size = file.stat().st_size
        logger.info("Uploading %s (%s bytes) to %s/%s", file.name, size, bucket, key)
        try:
            self._client.upload_file(
                Filename=str(file),
                Bucket=bucket,
                Key=key,
                ExtraArgs={"ContentType": _content_type(file)},
            )
        except _STORAGE_ERRORS as exc:
            raise StorageError(f"Failed to upload {file.name} to {bucket}/{key}: {exc}") from exc
        logger.info("Uploaded %s/%s", bucket, key)

    def _download_url(self, key: str) -> str:
        """Pre-signed GET URL, so the bucket itself can stay private."""
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.bucket, "Key": key},
                ExpiresIn=self._settings.link_expiry_seconds,
            )
        except _STORAGE_ERRORS as exc:
            raise StorageError(f"Failed to sign a download link for {key}: {exc}") from exc
        logger.info(
            "Signed download link for %s, valid for %ss",
            key,
            self._settings.link_expiry_seconds,
        )
        return url


def _content_type(file: Path) -> str:
    """So browsers download the archive instead of guessing at it."""
    return _CONTENT_TYPES.get(file.suffix.lower(), _DEFAULT_CONTENT_TYPE)
