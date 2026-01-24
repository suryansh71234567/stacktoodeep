"""
Route and Stop Pydantic Models.

This module defines models for vehicle routing and stops
used in the optimization output.
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ride import Location, TimeWindow


class Stop(BaseModel):
    """
    A single stop (pickup or dropoff) in a vehicle route.
    
    Represents one point where the vehicle stops to pick up
    or drop off passengers.
    """
    ride_id: str = Field(
        ...,
        description="ID of the associated ride request"
    )
    location: Location = Field(
        ...,
        description="Geographic location of this stop"
    )
    type: Literal["pickup", "dropoff"] = Field(
        ...,
        description="Whether this is a pickup or dropoff point"
    )
    time_window: TimeWindow = Field(
        ...,
        description="Acceptable time window for this stop"
    )
    num_passengers: int = Field(
        ...,
        ge=0,
        le=4,
        description="Number of passengers getting on (pickup) or off (dropoff)"
    )
    scheduled_time: Optional[datetime] = Field(
        default=None,
        description="Scheduled arrival time at this stop (set after optimization)"
    )
    sequence: int = Field(
        default=0,
        ge=0,
        description="Order of this stop in the route (0-indexed)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ride_id": "ride_123",
                "location": {
                    "latitude": 28.6139,
                    "longitude": 77.2090,
                    "address": "Connaught Place, Delhi"
                },
                "type": "pickup",
                "time_window": {
                    "earliest": "2026-01-24T08:45:00",
                    "preferred": "2026-01-24T09:00:00",
                    "latest": "2026-01-24T09:15:00"
                },
                "num_passengers": 2,
                "sequence": 0
            }
        }
    }


# Keep StopType for backward compatibility
class StopType:
    """Legacy stop type constants for backward compatibility."""
    PICKUP = "pickup"
    DROP = "dropoff"


class VehicleRoute(BaseModel):
    """
    Optimized route for a single vehicle.
    
    Contains the ordered sequence of stops, distance/duration metrics,
    capacity tracking, and revenue information.
    """
    vehicle_id: str = Field(
        ...,
        description="Unique identifier for the vehicle/driver"
    )
    stops: List[Stop] = Field(
        default_factory=list,
        description="Ordered list of stops (pickups and dropoffs)"
    )
    total_distance_km: float = Field(
        default=0.0,
        ge=0,
        description="Total route distance in kilometers"
    )
    total_duration_minutes: int = Field(
        default=0,
        ge=0,
        description="Total route duration in minutes"
    )
    capacity_used: int = Field(
        default=0,
        ge=0,
        le=4,
        description="Maximum passengers in vehicle at any point on route"
    )
    revenue: float = Field(
        default=0.0,
        ge=0,
        description="Total revenue for this route"
    )
    load_profile: List[int] = Field(
        default_factory=list,
        description="Passenger count after each stop (for capacity visualization)"
    )
    
    # Backward compatibility
    ride_request_ids: List[UUID] = Field(
        default_factory=list,
        description="IDs of all ride requests in this route (legacy)"
    )
    total_duration_min: float = Field(
        default=0.0,
        ge=0,
        description="Alias for total_duration_minutes (legacy)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "vehicle_id": "driver_456",
                "stops": [
                    {
                        "ride_id": "ride_123",
                        "location": {"latitude": 28.6139, "longitude": 77.2090},
                        "type": "pickup",
                        "time_window": {
                            "earliest": "2026-01-24T08:45:00",
                            "preferred": "2026-01-24T09:00:00",
                            "latest": "2026-01-24T09:15:00"
                        },
                        "num_passengers": 2,
                        "sequence": 0
                    }
                ],
                "total_distance_km": 15.5,
                "total_duration_minutes": 35,
                "capacity_used": 2,
                "revenue": 320.0,
                "load_profile": [2, 0]
            }
        }
    }
