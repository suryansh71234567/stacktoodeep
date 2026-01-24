"""
Ride request data models.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class RideRequest(BaseModel):
    """
    A single ride request from a user.
    
    Input format:
    - user_id: User identifier
    - location_start / location_end: Pickup and drop locations
    - ride_time: Preferred pickup time
    - buffer_time: Combined flexibility (applied as buffer_after_min)
    """
    id: UUID = Field(default_factory=uuid4, description="Unique ride request ID")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    pickup: Location = Field(..., alias="location_start", description="Pickup location")
    drop: Location = Field(..., alias="location_end", description="Drop-off location")
    preferred_time: datetime = Field(..., alias="ride_time", description="Preferred pickup time")
    buffer_before_min: int = Field(
        default=0, 
        ge=0, 
        le=120,
        description="Minutes user is willing to depart BEFORE preferred time"
    )
    buffer_after_min: int = Field(
        default=0, 
        ge=0, 
        le=120,
        alias="buffer_time",
        description="Minutes user is willing to depart AFTER preferred time"
    )

    class Config:
        populate_by_name = True  # Allow both alias and field name
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "location_start": {"lat": 28.6139, "lng": 77.2090},
                "location_end": {"lat": 28.5355, "lng": 77.3910},
                "ride_time": "2026-01-24T09:00:00",
                "buffer_time": 30
            }
        }
