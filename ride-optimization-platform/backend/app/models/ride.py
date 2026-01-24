"""
Ride API Pydantic Models.

This module defines all request/response models for the ride-sharing API.
Uses Pydantic v2 syntax with proper validation and documentation.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enums
# =============================================================================

class RideStatus(str, Enum):
    """
    Ride lifecycle status for API responses.
    
    Flow: REQUESTED -> OPTIMIZING -> BIDDING -> CONFIRMED -> IN_PROGRESS -> COMPLETED
                                             |
                                             -> CANCELLED (can happen at any stage)
    """
    REQUESTED = "requested"       # User submitted ride request
    OPTIMIZING = "optimizing"     # Being processed by optimization engine
    BIDDING = "bidding"           # AI agent negotiating with drivers
    CONFIRMED = "confirmed"       # Driver assigned, awaiting pickup
    IN_PROGRESS = "in_progress"   # Ride is currently happening
    COMPLETED = "completed"       # Ride finished successfully
    CANCELLED = "cancelled"       # Ride cancelled


# =============================================================================
# Core Models
# =============================================================================

class Location(BaseModel):
    """
    Geographic location with coordinates and optional address.
    
    Used for pickup and dropoff points.
    """
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude coordinate (-90 to 90)",
        examples=[28.6139]
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude coordinate (-180 to 180)",
        examples=[77.2090]
    )
    address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Human-readable address (optional)",
        examples=["Connaught Place, New Delhi"]
    )

    # Aliases for backward compatibility with existing code using lat/lng
    @property
    def lat(self) -> float:
        """Alias for latitude (backward compatibility)."""
        return self.latitude
    
    @property
    def lng(self) -> float:
        """Alias for longitude (backward compatibility)."""
        return self.longitude


class TimeWindow(BaseModel):
    """
    Time flexibility window for ride optimization.
    
    Specifies the acceptable time range for pickup, enabling
    better pooling opportunities and cost savings.
    """
    earliest: datetime = Field(
        ...,
        description="Earliest acceptable pickup time"
    )
    latest: datetime = Field(
        ...,
        description="Latest acceptable pickup time"
    )
    preferred: datetime = Field(
        ...,
        description="User's preferred pickup time"
    )

    @model_validator(mode='after')
    def validate_time_order(self) -> 'TimeWindow':
        """Ensure latest is after earliest and preferred is within range."""
        if self.latest <= self.earliest:
            raise ValueError("'latest' must be after 'earliest'")
        if self.preferred < self.earliest or self.preferred > self.latest:
            raise ValueError("'preferred' must be between 'earliest' and 'latest'")
        return self


# =============================================================================
# Request Models
# =============================================================================

class RideRequest(BaseModel):
    """
    Full internal representation of a ride request.
    
<<<<<<< HEAD
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
=======
    Used internally by the optimization engine and contains
    all ride details including computed fields.
    """
    id: UUID = Field(
        default_factory=uuid4,
        description="Unique ride request identifier"
    )
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User identifier from auth system"
    )
    pickup: Location = Field(
        ...,
        description="Pickup location"
    )
    dropoff: Location = Field(
        ...,
        description="Drop-off location"
    )
    time_window: TimeWindow = Field(
        ...,
        description="Acceptable time range for pickup"
    )
    num_passengers: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of passengers (1-4)"
    )
    max_detour_minutes: int = Field(
        default=15,
        ge=0,
        le=30,
        description="Maximum acceptable detour in minutes for pooling (0-30)"
    )
    max_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="User's maximum budget (optional)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when request was created"
    )
    status: RideStatus = Field(
        default=RideStatus.REQUESTED,
        description="Current ride status"
    )

    # Backward compatibility properties
    @property
    def drop(self) -> Location:
        """Alias for dropoff (backward compatibility)."""
        return self.dropoff
    
    @property
    def preferred_time(self) -> datetime:
        """Alias for time_window.preferred (backward compatibility)."""
        return self.time_window.preferred
    
    @property
    def buffer_before_min(self) -> int:
        """Computed buffer before preferred time (backward compatibility)."""
        delta = self.time_window.preferred - self.time_window.earliest
        return int(delta.total_seconds() / 60)
    
    @property
    def buffer_after_min(self) -> int:
        """Computed buffer after preferred time (backward compatibility)."""
        delta = self.time_window.latest - self.time_window.preferred
        return int(delta.total_seconds() / 60)

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_123",
                "pickup": {
                    "latitude": 28.6139,
                    "longitude": 77.2090,
                    "address": "Connaught Place, Delhi"
                },
                "dropoff": {
                    "latitude": 28.5355,
                    "longitude": 77.3910,
                    "address": "Noida Sector 18"
                },
                "time_window": {
                    "earliest": "2026-01-24T08:30:00",
                    "preferred": "2026-01-24T09:00:00",
                    "latest": "2026-01-24T09:30:00"
                },
                "num_passengers": 2,
                "max_detour_minutes": 15
>>>>>>> hackathon-demo
            }
        }
    }


class RideRequestCreate(BaseModel):
    """
    Simplified API input for creating a ride request.
    
    Frontend sends this simpler format, and the backend
    converts it to the full RideRequest model.
    """
    pickup_address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Pickup address (will be geocoded)"
    )
    dropoff_address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Drop-off address (will be geocoded)"
    )
    preferred_time: datetime = Field(
        ...,
        description="Preferred pickup time"
    )
    time_buffer_minutes: int = Field(
        default=30,
        ge=0,
        le=120,
        description="Flexibility buffer in minutes (creates time window ± this value)"
    )
    num_passengers: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of passengers (1-4)"
    )
    max_detour_minutes: int = Field(
        default=15,
        ge=0,
        le=30,
        description="Maximum acceptable detour for pooling (0-30 minutes)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "pickup_address": "Connaught Place, New Delhi",
                "dropoff_address": "Noida Sector 18, UP",
                "preferred_time": "2026-01-24T09:00:00",
                "time_buffer_minutes": 30,
                "num_passengers": 1,
                "max_detour_minutes": 15
            }
        }
    }


# =============================================================================
# Response Models
# =============================================================================

class PricingInfo(BaseModel):
    """Pricing breakdown for a ride."""
    original_price: float = Field(
        ...,
        ge=0,
        description="Original price before discounts"
    )
    discounted_price: float = Field(
        ...,
        ge=0,
        description="Final price after all discounts"
    )
    savings: float = Field(
        ...,
        ge=0,
        description="Amount saved in currency"
    )
    savings_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage saved (0-100)"
    )


class RideResponse(BaseModel):
    """
    Optimization output / API response for a ride.
    
    Contains all information needed by the frontend to display
    the ride details, pricing, and route.
    """
    ride_id: UUID = Field(
        ...,
        description="Unique ride identifier"
    )
    bundle_id: Optional[UUID] = Field(
        default=None,
        description="Bundle ID if ride is pooled with others"
    )
    vehicle_id: Optional[str] = Field(
        default=None,
        description="Assigned vehicle/driver identifier"
    )
    pickup_time: datetime = Field(
        ...,
        description="Scheduled pickup time"
    )
    dropoff_time: datetime = Field(
        ...,
        description="Estimated drop-off time"
    )
    estimated_duration_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated ride duration in minutes"
    )
    pricing: PricingInfo = Field(
        ...,
        description="Pricing breakdown"
    )
    route_polyline: Optional[str] = Field(
        default=None,
        description="Encoded polyline string for route visualization"
    )
    stops: List[Location] = Field(
        default_factory=list,
        description="Ordered list of stops on the route"
    )
    status: RideStatus = Field(
        ...,
        description="Current ride status"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ride_id": "550e8400-e29b-41d4-a716-446655440000",
                "bundle_id": "660e8400-e29b-41d4-a716-446655440001",
                "vehicle_id": "driver_456",
                "pickup_time": "2026-01-24T09:05:00",
                "dropoff_time": "2026-01-24T09:45:00",
                "estimated_duration_minutes": 40,
                "pricing": {
                    "original_price": 450.0,
                    "discounted_price": 320.0,
                    "savings": 130.0,
                    "savings_percentage": 28.9
                },
                "route_polyline": "u{~vFvyys@fE?",
                "stops": [
                    {"latitude": 28.6139, "longitude": 77.2090},
                    {"latitude": 28.5355, "longitude": 77.3910}
                ],
                "status": "confirmed"
            }
        }
    }
