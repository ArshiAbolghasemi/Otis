"""API models for the dataset endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UploadedData(BaseModel):
    """The stored dataset and the link that identifies it."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "dataset.zip",
                "key": "uploads/9f1c.../dataset.zip",
                "link": "https://<endpoint>/otis/uploads/9f1c.../dataset.zip?X-Amz-...",
            }
        }
    )

    filename: str
    key: str
    link: str
