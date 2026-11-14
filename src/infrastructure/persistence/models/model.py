"""Trained model ORM model for ML model metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.infrastructure.persistence.models.base import Base


class TrainedModelModel(Base):
    """Metadata for a trained ML model."""

    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=True)
    file_path = Column(String(500), nullable=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now())
    metrics = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<TrainedModelModel(id={self.id}, version={self.version!r})>"
