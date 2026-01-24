"""
Utility functions for optimization services.
"""
from typing import List
from app.models.ride import RideRequest


def compute_pooling_efficiency(cluster_size: int, total_rides: int) -> float:
    """
    Compute pooling efficiency for a bundle.
    
    Efficiency increases with more rides pooled together.
    Single ride = 0% efficiency, fully pooled = proportional efficiency.
    
    Args:
        cluster_size: Number of rides in the cluster
        total_rides: Total rides being optimized
        
    Returns:
        Efficiency ratio between 0.0 and 1.0
    """
    if cluster_size <= 1:
        return 0.0
    
    # More rides pooled = higher efficiency
    # Cap at 0.5 (50%) for realistic economic modeling
    efficiency = min(0.5, (cluster_size - 1) * 0.15)
    return efficiency


def compute_individual_route_distance(ride: RideRequest) -> float:
    """
    Compute the direct individual distance for a single ride.
    
    Used to compare against pooled routes.
    
    Args:
        ride: A ride request
        
    Returns:
        Direct distance in km
    """
    from app.services.optimization.routing import haversine_distance_km
    
    return haversine_distance_km(
        ride.pickup.lat, ride.pickup.lng,
        ride.drop.lat, ride.drop.lng
    )


def compute_total_individual_distance(rides: List[RideRequest]) -> float:
    """
    Compute total distance if all rides were taken individually.
    
    Args:
        rides: List of ride requests
        
    Returns:
        Sum of individual distances in km
    """
    return sum(compute_individual_route_distance(r) for r in rides)
