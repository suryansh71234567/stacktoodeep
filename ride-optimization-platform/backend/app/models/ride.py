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
    
    Contains pickup/drop locations, preferred time, and flexibility buffers
    that allow the optimizer to find better pooling opportunities.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique ride request ID")
    pickup: Location = Field(..., description="Pickup location")
    drop: Location = Field(..., description="Drop-off location")
    preferred_time: datetime = Field(..., description="Preferred pickup time")
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
        description="Minutes user is willing to depart AFTER preferred time"
    )
    user_id: Optional[str] = Field(default=None, description="Optional user identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "pickup": {"lat": 28.6139, "lng": 77.2090},
                "drop": {"lat": 28.5355, "lng": 77.3910},
                "preferred_time": "2026-01-24T09:00:00",
                "buffer_before_min": 15,
                "buffer_after_min": 30
            }
        }
