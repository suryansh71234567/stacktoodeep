"""
Route solver for ride clusters.
"""
from typing import List
from datetime import datetime, timedelta

from app.models.ride import RideRequest
from app.models.route import VehicleRoute, Stop, StopType
from app.services.optimization.routing import (
    haversine_distance_km, 
    estimate_route_distance_and_time
)


def solve_cluster(cluster: List[RideRequest]) -> VehicleRoute:
    """
    Solve routing for a cluster of pooled rides.
    
    Uses a simple greedy approach:
    1. Pick up all riders first (ordered by distance from first pickup)
    2. Drop off all riders (ordered by distance from last pickup)
    
    This is intentionally simple for hackathon scope.
    
    Args:
        cluster: List of pooled ride requests
        
    Returns:
        VehicleRoute with ordered stops and distance/duration metrics
    """
    if not cluster:
        return VehicleRoute(
            stops=[],
            total_distance_km=0.0,
            total_duration_min=0.0,
            ride_request_ids=[]
        )
    
    # Order pickups by distance from first pickup (greedy)
    ordered_pickups = order_by_distance(
        cluster,
        lambda r: (r.pickup.lat, r.pickup.lng),
        start_point=(cluster[0].pickup.lat, cluster[0].pickup.lng)
    )
    
    # Order drops by distance from last pickup location
    last_pickup = ordered_pickups[-1]
    ordered_drops = order_by_distance(
        cluster,
        lambda r: (r.drop.lat, r.drop.lng),
        start_point=(last_pickup.pickup.lat, last_pickup.pickup.lng)
    )
    
    # Build stops list
    stops = []
    sequence = 0
    
    # Add all pickups
    for ride in ordered_pickups:
        stop = Stop(
            ride_request_id=ride.id,
            lat=ride.pickup.lat,
            lng=ride.pickup.lng,
            stop_type=StopType.PICKUP,
            sequence=sequence
        )
        stops.append(stop)
        sequence += 1
    
    # Add all drops
    for ride in ordered_drops:
        stop = Stop(
            ride_request_id=ride.id,
            lat=ride.drop.lat,
            lng=ride.drop.lng,
            stop_type=StopType.DROP,
            sequence=sequence
        )
        stops.append(stop)
        sequence += 1
    
    # Calculate route metrics
    total_distance_km, total_duration_min = estimate_route_distance_and_time(stops)
    
    # Get all ride request IDs
    ride_request_ids = [ride.id for ride in cluster]
    
    return VehicleRoute(
        stops=stops,
        total_distance_km=total_distance_km,
        total_duration_min=total_duration_min,
        ride_request_ids=ride_request_ids
    )


def order_by_distance(
    rides: List[RideRequest],
    location_getter,
    start_point: tuple
) -> List[RideRequest]:
    """
    Order rides by distance from a starting point (greedy nearest neighbor).
    
    Args:
        rides: List of ride requests
        location_getter: Function to get (lat, lng) from a ride
        start_point: Starting coordinates (lat, lng)
        
    Returns:
        Ordered list of ride requests
    """
    if len(rides) <= 1:
        return list(rides)
    
    remaining = list(rides)
    ordered = []
    current_point = start_point
    
    while remaining:
        # Find nearest ride to current point
        nearest_idx = 0
        nearest_dist = float('inf')
        
        for i, ride in enumerate(remaining):
            loc = location_getter(ride)
            dist = haversine_distance_km(
                current_point[0], current_point[1],
                loc[0], loc[1]
            )
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i
        
        # Move to nearest ride
        nearest_ride = remaining.pop(nearest_idx)
        ordered.append(nearest_ride)
        current_point = location_getter(nearest_ride)
    
    return ordered
