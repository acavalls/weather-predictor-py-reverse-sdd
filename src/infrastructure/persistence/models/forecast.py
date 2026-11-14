"""Forecast ORM model for weather predictions."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from src.infrastructure.persistence.models.base import Base


class ForecastModel(Base):
    """Weather prediction record for a location and date."""

    __tablename__ = "forecasts"
    __table_args__ = (Index("idx_forecasts_location_date", "location_name", "predicted_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_name = Column(String(255), nullable=False)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    target_date = Column(DateTime(timezone=True), nullable=False)
    temperature = Column(Numeric, nullable=True)
    humidity = Column(Numeric, nullable=True)
    pressure = Column(Numeric, nullable=True)
    wind_speed = Column(Numeric, nullable=True)
    cloud_cover = Column(Numeric, nullable=True)
    wind_direction = Column(Numeric, nullable=True)
    dew_point = Column(Numeric, nullable=True)
    precipitation = Column(Numeric, nullable=True)
    model_version = Column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<ForecastModel(id={self.id}, location={self.location_name!r})>"
