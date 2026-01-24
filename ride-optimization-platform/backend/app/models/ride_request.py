"""
Pydantic model for RideRequest.
Represents a single ride request from a user.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class Location(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class RideRequest(BaseModel):
    """
    A single ride request submitted by a user.
    
    Attributes:
        request_id: Unique identifier for this request
        pickup: Pickup location coordinates
        drop: Drop-off location coordinates
        preferred_time: User's preferred pickup time (ISO 8601)
        buffer_before_min: Minutes before preferred_time user can accept pickup
        buffer_after_min: Minutes after preferred_time user can accept pickup
    """
    request_id: str = Field(..., description="Unique request identifier")
    pickup: Location = Field(..., description="Pickup location")
    drop: Location = Field(..., description="Drop-off location")
    preferred_time: datetime = Field(..., description="Preferred pickup time (ISO 8601)")
    buffer_before_min: int = Field(..., ge=0, description="Flexibility before preferred time (minutes)")
    buffer_after_min: int = Field(..., ge=0, description="Flexibility after preferred time (minutes)")
