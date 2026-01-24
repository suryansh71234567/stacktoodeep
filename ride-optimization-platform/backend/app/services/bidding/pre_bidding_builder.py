"""
D5: Pre-Bidding Data Builder

Builds the MINIMAL information that companies see BEFORE bidding.
This data hides sensitive user details while providing enough
information for companies to price the ride.
"""
from typing import Any, Dict

from app.services.bidding.utils import parse_iso_datetime, get_earliest_datetime


def build_pre_bidding_payload(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the pre-bidding payload from a RideBundle.
    
    This is a PURE function with NO side effects.
    
    Logic:
    - time = earliest pickup_time among users
    - duration = bundle.duration
    - distance = bundle.distance
    - max_bidding_price = cost_without_optimization * 0.9
    
    Args:
        bundle: RideBundle dict with the following structure:
            {
                "bundle_id": str,
                "route": str,
                "users": [{"user_id", "pickup_location", "pickup_time", 
                          "drop_location", "drop_time"}],
                "distance": float,
                "duration": float,
                "cost_without_optimization": float,
                "optimized_cost": float
            }
            
    Returns:
        Pre-bidding payload dict:
            {
                "bundle_id": str,
                "time": str (ISO format),
                "duration": float,
                "distance": float,
                "max_bidding_price": float
            }
            
    Raises:
        KeyError: If required fields are missing from bundle
        ValueError: If users list is empty
    """
    # Validate bundle has required fields
    required_fields = ['bundle_id', 'users', 'distance', 'duration', 'cost_without_optimization']
    for field in required_fields:
        if field not in bundle:
            raise KeyError(f"Bundle missing required field: {field}")
    
    users = bundle['users']
    if not users:
        raise ValueError("Bundle must have at least one user")
    
    # Extract earliest pickup time from all users
    pickup_times = [user['pickup_time'] for user in users]
    earliest_time = get_earliest_datetime(pickup_times)
    
    # Calculate max bidding price (90% of unoptimized cost)
    # This ensures companies see upside while platform keeps margin
    max_bidding_price = bundle['cost_without_optimization'] * 0.9
    
    return {
        "bundle_id": bundle['bundle_id'],
        "time": earliest_time.isoformat(),
        "duration": bundle['duration'],
        "distance": bundle['distance'],
        "max_bidding_price": round(max_bidding_price, 2)
    }
