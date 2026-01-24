"""
Route distance and duration estimation.
"""
import math
from typing import List, Tuple

from app.models.route import Stop


# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0

# Average speed assumption for duration estimation
AVERAGE_SPEED_KMH = 30.0


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula to compute distance in kilometers.
    
    Args:
        lat1: Latitude of first point (degrees)
        lng1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lng2: Longitude of second point (degrees)
        
    Returns:
        Distance in kilometers
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance_km = EARTH_RADIUS_KM * c
    return distance_km


def estimate_route_distance_and_time(stops: List[Stop]) -> Tuple[float, float]:
    """
    Estimate total distance and duration for a route.
    
    Sums haversine distances between consecutive stops and
    calculates duration assuming average speed of 30 km/h.
    
    Args:
        stops: Ordered list of stops in the route
        
    Returns:
        Tuple of (total_distance_km, total_duration_minutes)
    """
    if len(stops) < 2:
        return (0.0, 0.0)
    
    total_distance_km = 0.0
    
    for i in range(len(stops) - 1):
        current_stop = stops[i]
        next_stop = stops[i + 1]
        
        segment_distance = haversine_distance_km(
            current_stop.lat,
            current_stop.lng,
            next_stop.lat,
            next_stop.lng
        )
        total_distance_km += segment_distance
    
    # Duration = distance / speed, convert hours to minutes
    total_duration_min = (total_distance_km / AVERAGE_SPEED_KMH) * 60
    
    return (total_distance_km, total_duration_min)


def compute_distance_between_pickups(
    lat1: float, lng1: float, 
    lat2: float, lng2: float
) -> float:
    """
    Convenience function to check if two pickups are within pooling distance.
    
    Args:
        lat1, lng1: First pickup coordinates
        lat2, lng2: Second pickup coordinates
        
    Returns:
        Distance in km between the two pickup points
    """
    return haversine_distance_km(lat1, lng1, lat2, lng2)
