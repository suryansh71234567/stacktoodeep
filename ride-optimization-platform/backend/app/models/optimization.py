"""
Optimization Input/Output Pydantic Models.

This module defines models for the optimization API endpoint
including input parameters, output results, and metrics.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.ride import RideRequest, Location
from app.models.route import VehicleRoute
from app.models.pricing import PricingBreakdown


# =============================================================================
# Optimization Input
# =============================================================================

class OptimizationInput(BaseModel):
    """
    Input parameters for the ride optimization endpoint.
    
    Contains the list of rides to optimize along with
    configuration options for the optimization algorithm.
    """
    ride_requests: List[RideRequest] = Field(
        ...,
        min_length=1,
        description="List of ride requests to optimize"
    )
    available_vehicles: List[str] = Field(
        default_factory=list,
        description="List of available vehicle IDs (empty = auto-assign)"
    )
    optimization_objective: Literal["minimize_cost", "maximize_driver_profit"] = Field(
        default="minimize_cost",
        description="Optimization goal: minimize rider cost or maximize driver earnings"
    )
    max_computation_time_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum time for optimization solver (1-300 seconds)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ride_requests": [
                    {
                        "user_id": "user_123",
                        "pickup": {
                            "latitude": 29.8543,
                            "longitude": 77.8880,
                            "address": "IIT Roorkee"
                        },
                        "dropoff": {
                            "latitude": 30.3165,
                            "longitude": 78.0322,
                            "address": "Clock Tower, Dehradun"
                        },
                        "time_window": {
                            "earliest": "2026-01-27T09:00:00",
                            "preferred": "2026-01-27T10:00:00",
                            "latest": "2026-01-27T11:00:00"
                        },
                        "num_passengers": 1,
                        "max_detour_minutes": 15
                    }
                ],
                "available_vehicles": [],
                "optimization_objective": "minimize_cost",
                "max_computation_time_seconds": 30
            }
        }
    }


# =============================================================================
# User Ride Info (for bundle output)
# =============================================================================

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


# =============================================================================
# Optimization Metrics
# =============================================================================

class OptimizationMetrics(BaseModel):
    """
    Detailed metrics from the optimization process.
    """
    rides_pooled: int = Field(
        default=0,
        ge=0,
        description="Number of rides that were pooled with others"
    )
    vehicles_used: int = Field(
        default=0,
        ge=0,
        description="Number of vehicles assigned to routes"
    )
    average_detour_minutes: float = Field(
        default=0.0,
        ge=0,
        description="Average detour time added per rider due to pooling"
    )
    pooling_efficiency: float = Field(
        default=0.0,
        ge=0,
        description="Average rides per vehicle (higher = better pooling)"
    )
    total_distance_saved_km: float = Field(
        default=0.0,
        ge=0,
        description="Total distance saved compared to individual rides"
    )
    avg_pooling_efficiency: float = Field(
        default=0.0,
        ge=0,
        description="Legacy: same as pooling_efficiency"
    )


# =============================================================================
# Ride Bundle
# =============================================================================

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
    route: Union[str, VehicleRoute] = Field(..., description="Abstract route representation or polyline")
    
    # Per-user ride details
    users: List[UserRideInfo] = Field(default_factory=list, description="Per-user pickup/drop information")
    
    # Metrics
    distance: float = Field(default=0.0, ge=0, description="Total route distance in km")
    duration: float = Field(default=0.0, ge=0, description="Total route duration in minutes")
    
    # Cost comparison
    cost_without_optimization: float = Field(default=0.0, ge=0, description="Cost if rides taken separately")
    optimized_cost: float = Field(default=0.0, ge=0, description="Optimized pooled cost")
    
    # Additional fields for internal use
    ride_request_ids: List[str] = Field(default_factory=list, description="IDs of ride requests")
    detailed_route: Optional[VehicleRoute] = Field(default=None, description="Detailed route with stops")
    pricing: Optional[PricingBreakdown] = Field(default=None, description="Full pricing breakdown")
    time_window_start: Optional[datetime] = Field(default=None, description="Earliest departure time")
    time_window_end: Optional[datetime] = Field(default=None, description="Latest departure time")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Bundle creation timestamp")

    model_config = {
        "json_schema_extra": {
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
    }


# =============================================================================
# Optimization Output
# =============================================================================

class OptimizationOutput(BaseModel):
    """
    Output from the ride optimization endpoint.
    """
    bundles: List[RideBundle] = Field(
        default_factory=list, 
        description="List of optimized ride bundles"
    )
    total_rides_processed: int = Field(default=0, ge=0, description="Number of rides processed")
    total_bundles_created: int = Field(default=0, ge=0, description="Number of bundles created")
    optimization_metrics: Optional[Dict] = Field(
        default=None, 
        description="Additional optimization metrics"
    )

    model_config = {
        "json_schema_extra": {
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
    }
