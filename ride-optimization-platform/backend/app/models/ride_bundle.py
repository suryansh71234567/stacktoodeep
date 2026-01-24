"""
Pydantic model for RideBundle.
Represents a group of pooled ride requests ready for auction.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class RouteSummary(BaseModel):
    """Summary of the optimized route for this bundle."""
    total_distance_km: float = Field(..., description="Total distance in kilometers")
    estimated_duration_min: float = Field(..., description="Estimated duration in minutes")


class TimeWindow(BaseModel):
    """Time window for the bundle execution."""
    start: datetime = Field(..., description="Earliest start time")
    end: datetime = Field(..., description="Latest end time")


class BundleMetrics(BaseModel):
    """Quality metrics for the bundle."""
    flex_score: float = Field(..., description="Average flexibility score of pooled rides")
    pooling_efficiency: float = Field(..., ge=0, le=1, description="Pooling efficiency ratio (0-1)")


class BundlePricing(BaseModel):
    """Pricing breakdown for the bundle."""
    baseline_driver_profit: float = Field(..., description="Driver profit without optimization")
    optimized_driver_profit: float = Field(..., description="Driver profit with optimization")
    total_user_savings: float = Field(..., description="Total savings for all users in bundle")
    broker_commission: float = Field(..., description="Broker's commission (10% of optimized profit)")


class RideBundle(BaseModel):
    """
    A bundle of pooled ride requests ready for agentic negotiation and auction.
    
    Attributes:
        bundle_id: Unique identifier for this bundle
        ride_request_ids: List of request IDs included in this bundle
        route_summary: Distance and duration summary
        time_window: Execution time window
        metrics: Quality metrics
        pricing: Pricing breakdown
    """
    bundle_id: str = Field(..., description="Unique bundle identifier")
    ride_request_ids: List[str] = Field(..., description="IDs of requests in this bundle")
    route_summary: RouteSummary = Field(..., description="Route summary")
    time_window: TimeWindow = Field(..., description="Bundle time window")
    metrics: BundleMetrics = Field(..., description="Bundle quality metrics")
    pricing: BundlePricing = Field(..., description="Pricing breakdown")
