"""
Optimization input/output data models.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from app.models.ride import RideRequest
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
                        "pickup": {"lat": 28.6139, "lng": 77.2090},
                        "drop": {"lat": 28.5355, "lng": 77.3910},
                        "preferred_time": "2026-01-24T09:00:00",
                        "buffer_before_min": 15,
                        "buffer_after_min": 30
                    }
                ]
            }
        }


class RideBundle(BaseModel):
    """
    An optimized bundle of pooled rides.
    
    This is the primary output consumed by AI agents for bidding
    and blockchain contracts for auction/escrow.
    """
    bundle_id: UUID = Field(default_factory=uuid4, description="Unique bundle ID")
    ride_request_ids: List[UUID] = Field(
        ..., 
        description="IDs of ride requests in this bundle"
    )
    route: VehicleRoute = Field(..., description="Optimized route for this bundle")
    pricing: PricingBreakdown = Field(..., description="Economic breakdown")
    time_window_start: datetime = Field(..., description="Earliest departure time")
    time_window_end: datetime = Field(..., description="Latest departure time")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Bundle creation timestamp"
    )


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
