"""The AI Farm product catalogue.

The product id is what the AI Farm script dispatches on: it writes
``Product id ...,<id>`` as the first row of ``info.csv`` and the script runs
``<id>.py``.
"""

from __future__ import annotations

import re
from enum import Enum, IntEnum


class Product(IntEnum):
    """A model the user can order, identified by its AI Farm product id."""

    IMAGE_CLASSIFICATION = 1
    TIME_SERIES_CLASSIFICATION = 2
    TABULAR_FEATURES_CLASSIFICATION = 3
    MULTI_MODAL_CLASSIFICATION = 4
    IMAGE_REGRESSION = 5
    TIME_SERIES_REGRESSION = 6
    TABULAR_FEATURES_REGRESSION = 7
    MULTI_MODAL_REGRESSION = 8
    MULTI_MODAL_MULTI_HEAD_CLASSIFICATION_AND_REGRESSION = 9
    IMAGE_SEGMENTATION = 10
    IMAGE_DETECTION = 11

    @property
    def label(self) -> str:
        """Human readable name, as shown in the Porsline questionnaire."""
        return _LABELS[self]

    @classmethod
    def parse(cls, value: object) -> Product:
        """Coerce a questionnaire answer into a :class:`Product`.

        Accepts the id itself (``1``, ``"1"``) and the answer text with or
        without its leading number (``"1. Image Classification"``,
        ``"Image Classification"``). Raises ``ValueError`` otherwise.
        """
        if isinstance(value, Product):
            return value
        if isinstance(value, int):
            return cls._by_id(value)
        if isinstance(value, str):
            text = value.strip()
            if text.isdigit():
                return cls._by_id(int(text))
            # "1. Image Classification" / "1.Image Classification"
            leading_id = re.match(r"^\s*(\d+)\s*[.)-]?\s*", text)
            if leading_id:
                text = text[leading_id.end() :]
            product = _BY_LABEL.get(_normalise(text))
            if product is not None:
                return product
            if leading_id:
                return cls._by_id(int(leading_id.group(1)))
        raise ValueError(f"Unknown product {value!r}")

    @classmethod
    def _by_id(cls, product_id: int) -> Product:
        try:
            return cls(product_id)
        except ValueError:
            raise ValueError(f"Unknown product id {product_id}") from None


_LABELS: dict[Product, str] = {
    Product.IMAGE_CLASSIFICATION: "Image Classification",
    Product.TIME_SERIES_CLASSIFICATION: "Time Series Classification",
    Product.TABULAR_FEATURES_CLASSIFICATION: "Tabular Features Classification",
    Product.MULTI_MODAL_CLASSIFICATION: "Multi Modal Classification",
    Product.IMAGE_REGRESSION: "Image Regression",
    Product.TIME_SERIES_REGRESSION: "Time Series Regression",
    Product.TABULAR_FEATURES_REGRESSION: "Tabular Features Regression",
    Product.MULTI_MODAL_REGRESSION: "Multi Modal Regression",
    Product.MULTI_MODAL_MULTI_HEAD_CLASSIFICATION_AND_REGRESSION: (
        "Multi Modal Multi Head Classification and Regression"
    ),
    Product.IMAGE_SEGMENTATION: "Image Segmentation",
    Product.IMAGE_DETECTION: "Image Detection",
}


def _normalise(label: str) -> str:
    """Lower-case and collapse whitespace so answer text matches loosely."""
    return " ".join(label.lower().split())


_BY_LABEL: dict[str, Product] = {_normalise(label): product for product, label in _LABELS.items()}


class ModelSize(str, Enum):
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
