"""
Route and stop data models.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class StopType(str, Enum):
    """Type of stop in the route."""
    PICKUP = "pickup"
    DROP = "drop"


class Stop(BaseModel):
    """
    A single stop in a vehicle route.
    """
    ride_request_id: UUID = Field(..., description="ID of the associated ride request")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    stop_type: StopType = Field(..., description="Whether this is a pickup or drop")
    scheduled_time: Optional[datetime] = Field(
        default=None, 
        description="Scheduled arrival time at this stop"
    )
    sequence: int = Field(..., ge=0, description="Order of this stop in the route")


class VehicleRoute(BaseModel):
    """
    A complete route for a vehicle serving one or more ride requests.
    """
    stops: List[Stop] = Field(default_factory=list, description="Ordered list of stops")
    total_distance_km: float = Field(default=0.0, ge=0, description="Total route distance in km")
    total_duration_min: float = Field(default=0.0, ge=0, description="Total route duration in minutes")
    ride_request_ids: List[UUID] = Field(
        default_factory=list, 
        description="IDs of all ride requests in this route"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "stops": [
                    {
                        "ride_request_id": "550e8400-e29b-41d4-a716-446655440000",
                        "lat": 28.6139,
                        "lng": 77.2090,
                        "stop_type": "pickup",
                        "sequence": 0
                    }
                ],
                "total_distance_km": 15.5,
                "total_duration_min": 31.0,
                "ride_request_ids": ["550e8400-e29b-41d4-a716-446655440000"]
            }
        }
