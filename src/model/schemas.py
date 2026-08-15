"""API models for the model endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from aifarm.products import ModelSize, Product


class ModelRequest(BaseModel):
    """A request to train one model over an uploaded dataset."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "test@test.com",
                "upload_link": "https://test.com/dataset.zip",
                "model_size": "Medium",
                "product_id": 1,
            }
        }
    )

    email: EmailStr
    upload_link: str = Field(
        ...,
        min_length=1,
        description="The link returned by `POST /v1/data`.",
    )
    model_size: ModelSize
    product_id: Product = Field(
        ...,
        description=(
            "The ordered AI Farm product, as its id (1-11) or as its name, "
            "e.g. '1. Image Classification'."
        ),
    )

    @field_validator("product_id", mode="before")
    @classmethod
    def _parse_product(cls, value: object) -> Product:
        """Accept the answer as an id or as the product name."""
        return Product.parse(value)


class ModelResponse(BaseModel):
    """Response returned after a request is accepted."""

    model_config = ConfigDict(json_schema_extra={"example": {"id": 1, "status": "accepted"}})

    id: int
    status: str = "accepted"
