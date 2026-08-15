"""FastAPI dependencies for the dataset endpoint."""

from __future__ import annotations

from data.service import DataService


def get_data_service() -> DataService:
    return DataService()
