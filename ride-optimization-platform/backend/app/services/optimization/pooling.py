"""
Ride pooling logic - groups compatible rides into clusters.
"""
from typing import List, Tuple
from datetime import datetime

from app.models.ride import RideRequest
from app.utils.time_windows import compute_time_window, time_windows_overlap
from app.services.optimization.routing import haversine_distance_km


# Maximum pickup distance for rides to be pool-compatible (km)
MAX_PICKUP_DISTANCE_KM = 2.0


def are_rides_poolable(ride1: RideRequest, ride2: RideRequest) -> bool:
    """
    Check if two rides can be pooled together.
    
    Two rides are pool-compatible if:
    1. Pickup distance <= 2 km
    2. Their time windows overlap
    
    Args:
        ride1: First ride request
        ride2: Second ride request
        
    Returns:
        True if rides can be pooled, False otherwise
    """
    # Check pickup distance
    pickup_distance = haversine_distance_km(
        ride1.pickup.lat, ride1.pickup.lng,
        ride2.pickup.lat, ride2.pickup.lng
    )
    
    if pickup_distance > MAX_PICKUP_DISTANCE_KM:
        return False
    
    # Check time window overlap
    window1 = compute_time_window(
        ride1.preferred_time,
        ride1.buffer_before_min,
        ride1.buffer_after_min
    )
    window2 = compute_time_window(
        ride2.preferred_time,
        ride2.buffer_before_min,
        ride2.buffer_after_min
    )
    
    return time_windows_overlap(window1, window2)


def pool_rides(ride_requests: List[RideRequest]) -> List[List[RideRequest]]:
    """
    Group ride requests into poolable clusters using greedy algorithm.
    
    Algorithm:
    1. Start with first unassigned ride as cluster seed
    2. Find all rides poolable with the seed
    3. Add them to the cluster
    4. Repeat until all rides are assigned
    
    Note: Uses greedy clustering, not optimal graph partitioning.
    
    Args:
        ride_requests: List of ride requests to pool
        
    Returns:
        List of clusters, where each cluster is a list of poolable rides
    """
    if not ride_requests:
        return []
    
    # Track which rides have been assigned to a cluster
    assigned = set()
    clusters = []
    
    for i, seed_ride in enumerate(ride_requests):
        if i in assigned:
            continue
            
        # Start new cluster with this ride as seed
        cluster = [seed_ride]
        assigned.add(i)
        
        # Find all rides compatible with the seed
        for j, candidate_ride in enumerate(ride_requests):
            if j in assigned:
                continue
                
            # Check if candidate is poolable with seed
            if are_rides_poolable(seed_ride, candidate_ride):
                cluster.append(candidate_ride)
                assigned.add(j)
        
        clusters.append(cluster)
    
    return clusters


def compute_cluster_time_window(
    cluster: List[RideRequest]
) -> Tuple[datetime, datetime]:
    """
    Compute the common time window for a cluster of rides.
    
    Finds the intersection of all individual time windows.
    
    Args:
        cluster: List of pooled ride requests
        
    Returns:
        Tuple of (start_time, end_time) for the cluster
    """
    if not cluster:
        return None
    
    # Get all time windows
    windows = [
        compute_time_window(
            ride.preferred_time,
            ride.buffer_before_min,
            ride.buffer_after_min
        )
        for ride in cluster
    ]
    
    # Find intersection (latest start, earliest end)
    cluster_start = max(w[0] for w in windows)
    cluster_end = min(w[1] for w in windows)
    
    return (cluster_start, cluster_end)
