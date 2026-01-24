"""
Geographic utility functions.
"""

import math


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 (degrees)
        lng1: Longitude of point 1 (degrees)
        lat2: Latitude of point 2 (degrees)
        lng2: Longitude of point 2 (degrees)
    
    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def estimate_travel_time_min(distance_km: float) -> float:
    """
    Estimate travel time based on distance.
    Assumes average speed of 30 km/h.
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Estimated travel time in minutes
    """
    avg_speed_kmh = 30.0
    time_hours = distance_km / avg_speed_kmh
    time_minutes = time_hours * 60.0
    return time_minutes
