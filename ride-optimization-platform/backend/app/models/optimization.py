"""
Optimization Input/Output Pydantic Models.

This module defines models for the optimization API endpoint
including input parameters, output results, and metrics.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.ride import RideRequest, Location, TimeWindow
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
    rides: List[RideRequest] = Field(
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
    
    # Backward compatibility alias
    @property
    def ride_requests(self) -> List[RideRequest]:
        """Alias for rides (backward compatibility)."""
        return self.rides

    model_config = {
        "json_schema_extra": {
            "example": {
                "rides": [
                    {
                        "user_id": "user_123",
                        "pickup": {"latitude": 28.6139, "longitude": 77.2090},
                        "dropoff": {"latitude": 28.5355, "longitude": 77.3910},
                        "time_window": {
                            "earliest": "2026-01-24T08:30:00",
                            "preferred": "2026-01-24T09:00:00",
                            "latest": "2026-01-24T09:30:00"
                        },
                        "num_passengers": 1
                    }
                ],
                "available_vehicles": ["driver_1", "driver_2"],
                "optimization_objective": "minimize_cost",
                "max_computation_time_seconds": 30
            }
        }
    }


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
# Optimization Output
# =============================================================================

class OptimizationStatus:
    """Optimization result status constants."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class OptimizationOutput(BaseModel):
    """
    Output from the ride optimization endpoint.
    
    Contains the optimized routes, pricing, and metrics
    about the optimization process.
    """
    bundle_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this optimization batch"
    )
    routes: List[VehicleRoute] = Field(
        default_factory=list,
        description="List of optimized vehicle routes"
    )
    total_cost: float = Field(
        default=0.0,
        ge=0,
        description="Total cost for all rides in this batch"
    )
    total_savings: float = Field(
        default=0.0,
        ge=0,
        description="Total savings achieved through optimization"
    )
    optimization_time_seconds: float = Field(
        default=0.0,
        ge=0,
        description="Time taken by the optimization solver"
    )
    status: Literal["success", "partial", "failed"] = Field(
        default="success",
        description="Optimization result status"
    )
    metrics: OptimizationMetrics = Field(
        default_factory=OptimizationMetrics,
        description="Detailed optimization metrics"
    )
    
    # Backward compatibility fields
    bundles: List["RideBundle"] = Field(
        default_factory=list,
        description="Legacy: List of ride bundles"
    )
    total_rides_processed: int = Field(
        default=0,
        ge=0,
        description="Legacy: Number of rides processed"
    )
    total_bundles_created: int = Field(
        default=0,
        ge=0,
        description="Legacy: Number of bundles created"
    )
    optimization_metrics: Optional[Dict] = Field(
        default=None,
        description="Legacy: Additional metrics as dict"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
                "routes": [],
                "total_cost": 640.0,
                "total_savings": 130.0,
                "optimization_time_seconds": 2.5,
                "status": "success",
                "metrics": {
                    "rides_pooled": 3,
                    "vehicles_used": 2,
                    "average_detour_minutes": 5.2,
                    "pooling_efficiency": 1.5
                }
            }
        }
    }


# =============================================================================
# Ride Bundle (Legacy - kept for backward compatibility)
# =============================================================================

class RideBundle(BaseModel):
    """
    An optimized bundle of pooled rides.
    
    This is the primary output consumed by AI agents for bidding
    and blockchain contracts for auction/escrow.
    
    Note: This is a legacy model kept for backward compatibility.
    New code should use OptimizationOutput with routes.
    """
    bundle_id: UUID = Field(
        default_factory=uuid4,
        description="Unique bundle ID"
    )
    ride_request_ids: List[UUID] = Field(
        ...,
        description="IDs of ride requests in this bundle"
    )
    route: VehicleRoute = Field(
        ...,
        description="Optimized route for this bundle"
    )
    pricing: PricingBreakdown = Field(
        ...,
        description="Economic breakdown"
    )
    time_window_start: datetime = Field(
        ...,
        description="Earliest departure time"
    )
    time_window_end: datetime = Field(
        ...,
        description="Latest departure time"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Bundle creation timestamp"
    )
