"""
Bundle Builder.
Constructs RideBundle objects from pooled RideRequest lists.
"""

import uuid
from typing import List

from app.models.ride_request import RideRequest
from app.models.ride_bundle import (
    RideBundle,
    RouteSummary,
    TimeWindow,
    BundleMetrics,
    BundlePricing,
)
from app.utils.geo import haversine_distance_km, estimate_travel_time_min
from app.utils.time import compute_time_window
from app.services.discount_engine import compute_flex_score, compute_user_savings


def build_bundle(requests: List[RideRequest]) -> RideBundle:
    """
    Build a RideBundle from a list of pooled RideRequests.
    
    Steps:
    1. Generate unique bundle_id
    2. Calculate total distance (sum of pickup->drop for each request)
    3. Estimate duration from distance
    4. Compute time window (min start, max end of all requests)
    5. Compute metrics (average flex score, pooling efficiency)
    6. Compute pricing (baseline, optimized, savings, commission)
    
    Args:
        requests: List of pooled RideRequest objects
    
    Returns:
        RideBundle object
    """
    if not requests:
        raise ValueError("Cannot build bundle from empty request list")
    
    # 1. Generate bundle ID
    bundle_id = str(uuid.uuid4())
    
    # 2. Extract request IDs
    ride_request_ids = [r.request_id for r in requests]
    
    # 3. Calculate total distance (sum of pickup->drop)
    total_distance_km = 0.0
    for request in requests:
        distance = haversine_distance_km(
            request.pickup.lat,
            request.pickup.lng,
            request.drop.lat,
            request.drop.lng
        )
        total_distance_km += distance
    
    # 4. Estimate duration from total distance
    estimated_duration_min = estimate_travel_time_min(total_distance_km)
    
    route_summary = RouteSummary(
        total_distance_km=round(total_distance_km, 2),
        estimated_duration_min=round(estimated_duration_min, 2)
    )
    
    # 5. Compute time window
    all_windows = [
        compute_time_window(r.preferred_time, r.buffer_before_min, r.buffer_after_min)
        for r in requests
    ]
    
    time_window_start = min(w[0] for w in all_windows)
    time_window_end = max(w[1] for w in all_windows)
    
    time_window = TimeWindow(
        start=time_window_start,
        end=time_window_end
    )
    
    # 6. Compute metrics
    flex_scores = [
        compute_flex_score(r.buffer_before_min, r.buffer_after_min)
        for r in requests
    ]
    avg_flex_score = sum(flex_scores) / len(flex_scores)
    
    # Pooling efficiency: len(requests) / (len(requests) + 1)
    pooling_efficiency = len(requests) / (len(requests) + 1)
    
    metrics = BundleMetrics(
        flex_score=round(avg_flex_score, 2),
        pooling_efficiency=round(pooling_efficiency, 4)
    )
    
    # 7. Compute pricing
    # baseline_driver_profit = total_distance * 10
    baseline_driver_profit = total_distance_km * 10.0
    
    # optimized_driver_profit = baseline * (1 + pooling_efficiency)
    optimized_driver_profit = baseline_driver_profit * (1 + pooling_efficiency)
    
    # total_user_savings = sum of individual savings
    total_user_savings = sum(compute_user_savings(fs) for fs in flex_scores)
    
    # broker_commission = 10% of optimized_driver_profit
    broker_commission = optimized_driver_profit * 0.10
    
    pricing = BundlePricing(
        baseline_driver_profit=round(baseline_driver_profit, 2),
        optimized_driver_profit=round(optimized_driver_profit, 2),
        total_user_savings=round(total_user_savings, 2),
        broker_commission=round(broker_commission, 2)
    )
    
    return RideBundle(
        bundle_id=bundle_id,
        ride_request_ids=ride_request_ids,
        route_summary=route_summary,
        time_window=time_window,
        metrics=metrics,
        pricing=pricing
    )
