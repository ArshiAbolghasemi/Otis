"""FastAPI dependencies for the model endpoint."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from infrastructure.db.session import get_session
from model.service import ModelService


def get_model_service(session: Session = Depends(get_session)) -> ModelService:
    return ModelService(session)
