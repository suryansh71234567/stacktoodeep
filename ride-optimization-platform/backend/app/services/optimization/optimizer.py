"""
Main optimization orchestrator.
"""
from typing import List
from datetime import datetime

from app.models.ride import RideRequest
from app.models.optimization import (
    OptimizationInput, 
    OptimizationOutput, 
    RideBundle,
    RouteSummary,
    TimeWindow,
    BundleMetrics
)
from app.models.pricing import PricingBreakdown
from app.services.optimization.pooling import pool_rides, compute_cluster_time_window
from app.services.optimization.solver import solve_cluster
from app.services.optimization.utils import compute_pooling_efficiency
from app.services.discount_calculator import (
    compute_flex_score, 
    compute_user_savings
)
from app.services.pricing_engine import compute_pricing


def optimize_rides(ride_requests: List[RideRequest]) -> OptimizationOutput:
    """
    Main orchestration function for ride optimization.
    
    Flow:
    1. Compute time windows for each request
    2. Pool requests using greedy clustering
    3. For each pool:
       - Solve route
       - Compute metrics
       - Compute pricing
    4. Construct OptimizationOutput
    
    Args:
        ride_requests: List of ride requests to optimize
        
    Returns:
        OptimizationOutput with optimized bundles
    """
    if not ride_requests:
        return OptimizationOutput(
            bundles=[],
            total_rides_processed=0,
            total_bundles_created=0,
            optimization_metrics={}
        )
    
    # Step 1-2: Pool rides into clusters
    clusters = pool_rides(ride_requests)
    
    # Step 3: Process each cluster
    bundles = []
    total_user_savings = 0.0
    
    for cluster in clusters:
        # Solve route for this cluster
        route = solve_cluster(cluster)
        
        # Compute cluster time window
        time_window = compute_cluster_time_window(cluster)
        
        # Compute flex score and user savings for this cluster
        cluster_flex_score = 0.0
        cluster_savings = 0.0
        for ride in cluster:
            flex_score = compute_flex_score(
                ride.buffer_before_min,
                ride.buffer_after_min
            )
            cluster_flex_score += flex_score
            cluster_savings += compute_user_savings(flex_score)
        
        total_user_savings += cluster_savings
        
        # Compute pooling efficiency
        pooling_efficiency = compute_pooling_efficiency(
            len(cluster), 
            len(ride_requests)
        )
        
        # Compute pricing
        pricing = compute_pricing(
            route_distance_km=route.total_distance_km,
            pooling_efficiency=pooling_efficiency,
            total_user_savings=cluster_savings
        )
        
        # Create bundle (matching shared schema)
        bundle = RideBundle(
            ride_request_ids=[str(ride.id) for ride in cluster],
            route_summary=RouteSummary(
                total_distance_km=route.total_distance_km,
                estimated_duration_min=route.total_duration_min
            ),
            time_window=TimeWindow(
                start=time_window[0] if time_window else datetime.utcnow(),
                end=time_window[1] if time_window else datetime.utcnow()
            ),
            metrics=BundleMetrics(
                flex_score=cluster_flex_score,
                pooling_efficiency=pooling_efficiency
            ),
            pricing=pricing,
            route=route  # Keep detailed route for internal use
        )
        bundles.append(bundle)
    
    # Compute optimization metrics
    avg_pooling_efficiency = sum(
        compute_pooling_efficiency(len(c), len(ride_requests)) 
        for c in clusters
    ) / len(clusters) if clusters else 0.0
    
    optimization_metrics = {
        "avg_pooling_efficiency": round(avg_pooling_efficiency, 4),
        "total_user_savings": round(total_user_savings, 2),
        "total_clusters": len(clusters),
        "avg_cluster_size": round(len(ride_requests) / len(clusters), 2) if clusters else 0
    }
    
    return OptimizationOutput(
        bundles=bundles,
        total_rides_processed=len(ride_requests),
        total_bundles_created=len(bundles),
        optimization_metrics=optimization_metrics
    )
