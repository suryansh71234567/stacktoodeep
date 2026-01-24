"""
Optimization Engine.
Groups RideRequests into pools using greedy clustering.
"""

from typing import List

from app.models.ride_request import RideRequest
from app.utils.geo import haversine_distance_km
from app.utils.time import compute_time_window, time_windows_overlap


def optimize_ride_requests(requests: List[RideRequest]) -> List[List[RideRequest]]:
    """
    Optimize ride requests by grouping them into pools.
    
    Pooling criteria:
    - Pickup distance <= 2 km
    - Time windows overlap
    
    Uses greedy clustering: iterate through requests and add to existing
    pool if compatible, otherwise create new pool.
    
    Args:
        requests: List of RideRequest objects
    
    Returns:
        List of pools, where each pool is a list of RideRequest objects
    """
    if not requests:
        return []
    
    MAX_PICKUP_DISTANCE_KM = 2.0
    
    pools: List[List[RideRequest]] = []
    
    for request in requests:
        # Compute time window for this request
        request_window = compute_time_window(
            request.preferred_time,
            request.buffer_before_min,
            request.buffer_after_min
        )
        
        placed = False
        
        # Try to add to existing pool
        for pool in pools:
            # Check compatibility with ALL requests in the pool
            compatible = True
            for existing_request in pool:
                # Check pickup distance
                pickup_distance = haversine_distance_km(
                    request.pickup.lat,
                    request.pickup.lng,
                    existing_request.pickup.lat,
                    existing_request.pickup.lng
                )
                
                if pickup_distance > MAX_PICKUP_DISTANCE_KM:
                    compatible = False
                    break
                
                # Check time window overlap
                existing_window = compute_time_window(
                    existing_request.preferred_time,
                    existing_request.buffer_before_min,
                    existing_request.buffer_after_min
                )
                
                if not time_windows_overlap(request_window, existing_window):
                    compatible = False
                    break
            
            if compatible:
                pool.append(request)
                placed = True
                break
        
        # Create new pool if not placed
        if not placed:
            pools.append([request])
    
    return pools
