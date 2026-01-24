"""
Data models for the ride optimization platform.
"""
from app.models.ride import (
    RideStatus,
    Location,
    TimeWindow,
    RideRequest,
    RideRequestCreate,
    PricingInfo,
    RideResponse,
)
from app.models.route import VehicleRoute, Stop, StopType
from app.models.pricing import PricingBreakdown
from app.models.optimization import (
    OptimizationInput,
    OptimizationOutput,
    OptimizationMetrics,
    RideBundle,
)

__all__ = [
    # Ride models
    "RideStatus",
    "Location",
    "TimeWindow",
    "RideRequest",
    "RideRequestCreate",
    "PricingInfo",
    "RideResponse",
    # Route models
    "VehicleRoute",
    "Stop",
    "StopType",
    # Pricing models
    "PricingBreakdown",
    # Optimization models
    "OptimizationInput",
    "OptimizationOutput",
    "OptimizationMetrics",
    "RideBundle",
]
