"""
Optimization input/output data models.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.models.ride import RideRequest, Location
from app.models.route import VehicleRoute
from app.models.pricing import PricingBreakdown


class OptimizationInput(BaseModel):
    """
    Input for the ride optimization endpoint.
    """
    ride_requests: List[RideRequest] = Field(
        ..., 
        min_length=1,
        description="List of ride requests to optimize"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ride_requests": [
                    {
                        "user_id": "user_123",
                        "location_start": {"lat": 28.6139, "lng": 77.2090},
                        "location_end": {"lat": 28.5355, "lng": 77.3910},
                        "ride_time": "2026-01-24T09:00:00",
                        "buffer_time": 30
                    }
                ]
            }
        }


class UserRideInfo(BaseModel):
    """
    Per-user ride information in a bundle.
    Matches deliverable D3 output format.
    """
    user_id: str = Field(..., description="User identifier")
    pickup_location: Location = Field(..., description="Pickup coordinates")
    pickup_time: datetime = Field(..., description="Scheduled pickup time")
    drop_location: Location = Field(..., description="Drop-off coordinates")
    drop_time: datetime = Field(..., description="Estimated drop-off time")


class RideBundle(BaseModel):
    """
    An optimized bundle of pooled rides.
    
    Matches deliverable D3 output format:
    - bundle_id
    - route (abstract route / polyline)
    - users[] with pickup/drop times
    - distance, duration
    - cost_without_optimization, optimized_cost
    """
    bundle_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique bundle ID")
    
    # Route information
    route: str = Field(..., description="Abstract route representation or polyline")
    
    # Per-user ride details
    users: List[UserRideInfo] = Field(..., description="Per-user pickup/drop information")
    
    # Metrics
    distance: float = Field(..., ge=0, description="Total route distance in km")
    duration: float = Field(..., ge=0, description="Total route duration in minutes")
    
    # Cost comparison
    cost_without_optimization: float = Field(..., ge=0, description="Cost if rides taken separately")
    optimized_cost: float = Field(..., ge=0, description="Optimized pooled cost")
    
    # Additional fields for internal use
    ride_request_ids: List[str] = Field(default_factory=list, description="IDs of ride requests")
    detailed_route: Optional[VehicleRoute] = Field(default=None, description="Detailed route with stops")
    pricing: Optional[PricingBreakdown] = Field(default=None, description="Full pricing breakdown")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
                "route": "pickup1->pickup2->drop1->drop2",
                "users": [
                    {
                        "user_id": "user_123",
                        "pickup_location": {"lat": 28.6139, "lng": 77.2090},
                        "pickup_time": "2026-01-24T09:00:00",
                        "drop_location": {"lat": 28.5355, "lng": 77.3910},
                        "drop_time": "2026-01-24T09:30:00"
                    }
                ],
                "distance": 15.5,
                "duration": 31.0,
                "cost_without_optimization": 200.0,
                "optimized_cost": 150.0
            }
        }


class OptimizationOutput(BaseModel):
    """
    Output from the ride optimization endpoint.
    """
    bundles: List[RideBundle] = Field(
        default_factory=list, 
        description="List of optimized ride bundles"
    )
    total_rides_processed: int = Field(..., ge=0, description="Number of rides processed")
    total_bundles_created: int = Field(..., ge=0, description="Number of bundles created")
    optimization_metrics: Optional[dict] = Field(
        default=None, 
        description="Additional optimization metrics"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "bundles": [],
                "total_rides_processed": 4,
                "total_bundles_created": 2,
                "optimization_metrics": {
                    "avg_pooling_efficiency": 0.25,
                    "total_distance_saved_km": 12.5
                }
            }
        }
