"""API models for the webhook endpoint."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ModelSize(str, Enum):
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class ModelType(str, Enum):
    LINEAR_REGRESSION = "Linear Regression"
    LOGISTIC_REGRESSION = "Logistic Regression"
    RANDOM_FOREST = "Random Forest"


class WebhookPayload(BaseModel):
    """Inbound Porsline webhook payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "test@test.com",
                "upload_link": "https://test.com",
                "model_size": "Medium",
                "model_type": "Linear Regression",
            }
        }
    )

    email: EmailStr
    upload_link: str = Field(..., min_length=1)
    model_size: ModelSize
    model_type: ModelType


class WebhookResponse(BaseModel):
    """Response returned after a submission is accepted."""

    model_config = ConfigDict(json_schema_extra={"example": {"id": 1, "status": "accepted"}})

    id: int
    status: str = "accepted"
