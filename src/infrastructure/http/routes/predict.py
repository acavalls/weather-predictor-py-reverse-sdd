"""Predict route — POST /predict debug endpoint."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.predict.command import PredictCommand
from src.application.predict.port import IPredictUseCase
from src.domain.shared.errors import NotFoundError
from src.infrastructure.config.di import container

router = APIRouter()


def get_predict_use_case() -> IPredictUseCase:
    """Dependency factory — resolves PredictUseCase from DI container."""
    return container.predict_use_case()


class PredictRequest(BaseModel):
    """Request body for POST /predict.

    Attributes:
        location: City name for the prediction.
        horizons: Optional prediction horizons in hours.
    """

    location: str = Field(..., min_length=1, description="City name")
    horizons: List[int] = Field(
        default=[6, 12, 24],
        description="Prediction horizons in hours (default: [6, 12, 24])",
    )


class HorizonPrediction(BaseModel):
    """Predictions for a single horizon."""

    temperature_2m: float
    relative_humidity_2m: float
    surface_pressure: float
    wind_speed_10m: float
    cloud_cover: float
    precipitation: float


class PredictResponse(BaseModel):
    """Response body for POST /predict.

    Attributes:
        city: Requested city name.
        location_name: Resolved location name.
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        predictions: Dict mapping horizon hours to predicted values.
        model_version: Model version hash.
    """

    city: str
    location_name: str
    latitude: float
    longitude: float
    predictions: Dict[int, HorizonPrediction]
    model_version: str


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict weather for a city",
    description="Get ML-based weather predictions for multiple horizons.",
)
async def predict(
    request: PredictRequest,
    use_case: IPredictUseCase = Depends(get_predict_use_case),
) -> PredictResponse:
    """Handle POST /predict requests.

    Adapts HTTP request → PredictCommand → use case → HTTP response.
    """
    try:
        command = PredictCommand(
            city=request.location,
            horizons=request.horizons,
        )
        result = await use_case.execute(command)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Convert nested dicts to Pydantic models
    predictions = {horizon: HorizonPrediction(**values) for horizon, values in result.predictions.items()}

    return PredictResponse(
        city=result.city,
        location_name=result.location_name,
        latitude=result.latitude,
        longitude=result.longitude,
        predictions=predictions,
        model_version=result.model_version,
    )
