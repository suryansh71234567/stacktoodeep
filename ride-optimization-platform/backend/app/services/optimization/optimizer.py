"""
Main optimization orchestrator.
"""
from typing import List
from datetime import datetime, timedelta

from app.models.ride import RideRequest, Location
from app.models.optimization import (
    OptimizationInput, 
    OptimizationOutput, 
    RideBundle,
    UserRideInfo
)
from app.models.route import StopType
from app.services.optimization.pooling import pool_rides, compute_cluster_time_window
from app.services.optimization.solver import solve_cluster
from app.services.optimization.utils import (
    compute_pooling_efficiency,
    compute_individual_route_distance
)
from app.services.discount_calculator import (
    compute_flex_score, 
    compute_user_savings
)
from app.services.pricing_engine import compute_pricing


def generate_route_string(cluster: List[RideRequest], route) -> str:
    """
    Generate abstract route representation from stops.
    Format: pickup1->pickup2->drop1->drop2
    """
    if not route or not route.stops:
        return ""
    
    route_parts = []
    for stop in route.stops:
        # Find user_id for this stop
        user_id = "unknown"
        for ride in cluster:
            if str(ride.id) == str(stop.ride_request_id):
                user_id = ride.user_id or str(ride.id)[:8]
                break
        
        if stop.stop_type == StopType.PICKUP:
            route_parts.append(f"pickup_{user_id}")
        else:
            route_parts.append(f"drop_{user_id}")
    
    return "->".join(route_parts)


def compute_user_times(cluster: List[RideRequest], route, cluster_start: datetime) -> List[UserRideInfo]:
    """
    Compute per-user pickup and drop times based on route sequence.
    """
    users_info = []
    
    # Build stop sequence with cumulative times
    current_time = cluster_start
    stop_times = {}
    
    # Assume 30 km/h average speed, compute time between stops
    from app.services.optimization.routing import haversine_distance_km, AVERAGE_SPEED_KMH
    
    for i, stop in enumerate(route.stops):
        if i > 0:
            prev_stop = route.stops[i - 1]
            dist = haversine_distance_km(
                prev_stop.lat, prev_stop.lng,
                stop.lat, stop.lng
            )
            travel_time_min = (dist / AVERAGE_SPEED_KMH) * 60
            current_time = current_time + timedelta(minutes=travel_time_min)
        
        key = (str(stop.ride_request_id), stop.stop_type.value)
        stop_times[key] = current_time
    
    # Build user info list
    for ride in cluster:
        ride_id_str = str(ride.id)
        
        pickup_time = stop_times.get((ride_id_str, "pickup"), cluster_start)
        drop_time = stop_times.get((ride_id_str, "drop"), cluster_start + timedelta(minutes=30))
        
        user_info = UserRideInfo(
            user_id=ride.user_id or ride_id_str[:8],
            pickup_location=ride.pickup,
            pickup_time=pickup_time,
            drop_location=ride.drop,
            drop_time=drop_time
        )
        users_info.append(user_info)
    
    return users_info


def optimize_rides(ride_requests: List[RideRequest]) -> OptimizationOutput:
    """
    Main orchestration function for ride optimization.
    
    Produces output matching deliverable D3:
    - bundle_id
    - route (abstract route string)
    - users[] with pickup/drop times
    - distance, duration
    - cost_without_optimization, optimized_cost
    
    Constraints:
    - Max 4 users per car
    - Respect buffer windows
    """
    if not ride_requests:
        return OptimizationOutput(
            bundles=[],
            total_rides_processed=0,
            total_bundles_created=0,
            optimization_metrics={}
        )
    
    # Pool rides into clusters (max 4 per cluster)
    clusters = pool_rides(ride_requests)
    
    # Process each cluster
    bundles = []
    total_user_savings = 0.0
    
    for cluster in clusters:
        # Solve route for this cluster
        route = solve_cluster(cluster)
        
        # Compute cluster time window
        time_window = compute_cluster_time_window(cluster)
        cluster_start = time_window[0] if time_window else datetime.utcnow()
        
        # Compute cost without optimization (sum of individual rides)
        cost_without_optimization = sum(
            compute_individual_route_distance(ride) * 10  # $10 per km
            for ride in cluster
        )
        
        # Compute pooling efficiency and user savings
        cluster_savings = 0.0
        for ride in cluster:
            flex_score = compute_flex_score(
                ride.buffer_before_min,
                ride.buffer_after_min
            )
            cluster_savings += compute_user_savings(flex_score)
        
        total_user_savings += cluster_savings
        
        pooling_efficiency = compute_pooling_efficiency(
            len(cluster), 
            len(ride_requests)
        )
        
        # Compute optimized cost
        optimized_cost = route.total_distance_km * 10  # $10 per km for pooled route
        
        # Generate route string
        route_string = generate_route_string(cluster, route)
        
        # Compute per-user times
        users_info = compute_user_times(cluster, route, cluster_start)
        
        # Get pricing breakdown
        pricing = compute_pricing(
            route_distance_km=route.total_distance_km,
            pooling_efficiency=pooling_efficiency,
            total_user_savings=cluster_savings
        )
        
        # Create bundle (matching D3 format)
        bundle = RideBundle(
            route=route_string,
            users=users_info,
            distance=route.total_distance_km,
            duration=route.total_duration_min,
            cost_without_optimization=round(cost_without_optimization, 2),
            optimized_cost=round(optimized_cost, 2),
            ride_request_ids=[str(ride.id) for ride in cluster],
            detailed_route=route,
            pricing=pricing
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
