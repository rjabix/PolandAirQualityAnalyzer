"""
Pydantic v2 models for the smog API response format.

Each file represents a single snapshot in time containing readings
from multiple weather/air-quality stations (schools).

Usage:
    from smog_models import SmogApiResponse

    with open("smog_api_2026-03-18-18-19-34-CET") as f:
        response = SmogApiResponse.model_validate_json(f.read())

    for reading in response.smog_data:
        print(reading.school.city, reading.data.pm25_avg, reading.timestamp)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class StationLocation(BaseModel):
    """Physical location and identification of a monitoring station."""

    name: str
    street: Optional[str] = None  # Can be null or empty string in the source data
    post_code: str
    city: str

    # Coordinates come as strings in the API — parsed to float on load
    longitude: float
    latitude: float

    @field_validator("longitude", "latitude", mode="before")
    @classmethod
    def parse_coordinate(cls, v: str | float) -> float:
        """Coordinates are serialized as strings in the JSON; coerce to float."""
        return float(v)

    @field_validator("street", mode="before")
    @classmethod
    def normalize_street(cls, v: Optional[str]) -> Optional[str]:
        """Treat empty strings the same as null — no street info available."""
        if v is not None and v.strip() == "":
            return None
        return v


class AirQualityReading(BaseModel):
    """Averaged sensor measurements for a single time window."""

    humidity_avg: float = Field(ge=0, le=100, description="Relative humidity (%)")
    pressure_avg: float = Field(gt=0, description="Atmospheric pressure (hPa)")
    temperature_avg: float = Field(description="Temperature (°C)")
    pm10_avg: float = Field(ge=0, description="PM10 particulate matter (µg/m³)")
    pm25_avg: float = Field(ge=0, description="PM2.5 particulate matter (µg/m³)")


class StationReading(BaseModel):
    """A single station's full reading for one point in time."""

    school: StationLocation
    data: AirQualityReading
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: str | datetime) -> datetime:
        """Parse the 'YYYY-MM-DD HH:MM:SS' timestamp string."""
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Convenience properties for timeline analysis
    # ------------------------------------------------------------------

    @property
    def station_id(self) -> str:
        """Stable identifier for a station across multiple snapshot files."""
        return f"{self.school.post_code}_{self.school.name}"

    @property
    def air_quality_index(self) -> str:
        """
        Simple WHO-based PM2.5 band label for quick bucketing.
        Bands (µg/m³): Good <10 | Moderate 10–25 | Unhealthy 25–50 | Hazardous >50
        """
        pm25 = self.data.pm25_avg
        if pm25 < 10:
            return "Good"
        elif pm25 < 25:
            return "Moderate"
        elif pm25 < 50:
            return "Unhealthy"
        return "Hazardous"


class SmogApiResponse(BaseModel):
    """
    Top-level model for one snapshot file from the smog API.

    The filename encodes the capture time (e.g. smog_api_2026-03-18-18-19-34-CET)
    but the timestamp is also present on every individual reading.
    """

    smog_data: list[StationReading]
    it_has_next_page: bool = False
    pages_total: Optional[int] = None

    @model_validator(mode="after")
    def warn_if_paginated(self) -> SmogApiResponse:
        """
        Raise if there are more pages — the caller should fetch them all
        before treating this response as a complete snapshot.
        """
        if self.it_has_next_page:
            raise ValueError(
                "Response has additional pages (it_has_next_page=True). "
                "Fetch all pages before constructing a SmogApiResponse."
            )
        return self

    # ------------------------------------------------------------------
    # Helpers for timeline analysis across many snapshot files
    # ------------------------------------------------------------------

    @property
    def snapshot_timestamp(self) -> Optional[datetime]:
        """The shared timestamp of all readings (None if list is empty)."""
        if self.smog_data:
            return self.smog_data[0].timestamp
        return None

    def to_flat_records(self) -> list[dict]:
        """
        Flatten all station readings into plain dicts — ready for a
        pandas DataFrame or direct insertion into a database.

        Each record includes a 'snapshot_timestamp' key so rows from
        different files can be stacked and sorted on a timeline.
        """
        records = []
        for reading in self.smog_data:
            records.append({
                # Station identity
                "station_id":    reading.station_id,
                "station_name":  reading.school.name,
                "city":          reading.school.city,
                "post_code":     reading.school.post_code,
                "street":        reading.school.street,
                "latitude":      reading.school.latitude,
                "longitude":     reading.school.longitude,
                # Time
                "timestamp":     reading.timestamp,
                # Sensor data
                "humidity_avg":     reading.data.humidity_avg,
                "pressure_avg":     reading.data.pressure_avg,
                "temperature_avg":  reading.data.temperature_avg,
                "pm10_avg":         reading.data.pm10_avg,
                "pm25_avg":         reading.data.pm25_avg,
                # Derived
                "air_quality_index": reading.air_quality_index,
            })
        return records