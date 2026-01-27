"""
Optimization API endpoint.
"""
import math
import random
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.optimization import OptimizationInput, OptimizationOutput
from app.models.ride import RideRequest, Location, TimeWindow
from app.services.optimization.optimizer import optimize_rides


router = APIRouter(prefix="/optimize", tags=["optimization"])


def generate_dynamic_dummy_users(
    user_pickup: Location,
    user_dropoff: Location,
    user_time_window: TimeWindow,
    count: int = 20
) -> List[RideRequest]:
    """
    Generate dummy users dynamically based on user's route.
    
    The dummy users are spread within a circle that bounds the user's
    source and destination coordinates, with similar departure times.
    
    Args:
        user_pickup: User's pickup location
        user_dropoff: User's dropoff location
        user_time_window: User's time window for departure
        count: Number of dummy users to generate (default 20)
    
    Returns:
        List of RideRequest objects for dummy users
    """
    # Calculate center point (midpoint between pickup and dropoff)
    center_lat = (user_pickup.latitude + user_dropoff.latitude) / 2
    center_lng = (user_pickup.longitude + user_dropoff.longitude) / 2
    
    # Calculate radius (half the distance between pickup and dropoff + some buffer)
    lat_diff = abs(user_pickup.latitude - user_dropoff.latitude)
    lng_diff = abs(user_pickup.longitude - user_dropoff.longitude)
    # Distance in degrees, convert to approximate km (1 degree ≈ 111 km)
    distance_deg = math.sqrt(lat_diff ** 2 + lng_diff ** 2)
    radius_deg = (distance_deg / 2) + 0.05  # Add 5km buffer (0.05 degrees ≈ 5.5km)
    
    # Ensure minimum radius of 10km
    min_radius_deg = 0.09  # ~10km
    radius_deg = max(radius_deg, min_radius_deg)
    
    dummy_users = []
    
    for i in range(count):
        # Generate random pickup within the bounding circle
        pickup_angle = random.uniform(0, 2 * math.pi)
        pickup_r = radius_deg * math.sqrt(random.uniform(0.1, 1))
        pickup_lat = center_lat + pickup_r * math.cos(pickup_angle)
        pickup_lng = center_lng + pickup_r * math.sin(pickup_angle)
        
        # Generate random dropoff within the bounding circle (different from pickup)
        dropoff_angle = random.uniform(0, 2 * math.pi)
        dropoff_r = radius_deg * math.sqrt(random.uniform(0.1, 1))
        dropoff_lat = center_lat + dropoff_r * math.cos(dropoff_angle)
        dropoff_lng = center_lng + dropoff_r * math.sin(dropoff_angle)
        
        # Ensure pickup and dropoff are at least 2km apart
        while abs(pickup_lat - dropoff_lat) < 0.02 and abs(pickup_lng - dropoff_lng) < 0.02:
            dropoff_angle = random.uniform(0, 2 * math.pi)
            dropoff_r = radius_deg * math.sqrt(random.uniform(0.1, 1))
            dropoff_lat = center_lat + dropoff_r * math.cos(dropoff_angle)
            dropoff_lng = center_lng + dropoff_r * math.sin(dropoff_angle)
        
        # Generate time around user's preferred time (±30 minutes)
        time_offset_minutes = random.randint(-30, 30)
        preferred_time = user_time_window.preferred + timedelta(minutes=time_offset_minutes)
        
        # Create time window for dummy user
        buffer_before = random.randint(5, 20)
        buffer_after = random.randint(10, 40)
        
        dummy_time_window = TimeWindow(
            earliest=preferred_time - timedelta(minutes=buffer_before),
            preferred=preferred_time,
            latest=preferred_time + timedelta(minutes=buffer_after)
        )
        
        # Create the dummy ride request
        dummy_ride = RideRequest(
            user_id=f"dummy_user_{i+1:03d}",
            pickup=Location(
                latitude=round(pickup_lat, 6),
                longitude=round(pickup_lng, 6),
                address=f"Auto-generated pickup {i+1}"
            ),
            dropoff=Location(
                latitude=round(dropoff_lat, 6),
                longitude=round(dropoff_lng, 6),
                address=f"Auto-generated dropoff {i+1}"
            ),
            time_window=dummy_time_window,
            num_passengers=random.randint(1, 3),
            max_detour_minutes=random.randint(10, 25)
        )
        
        dummy_users.append(dummy_ride)
    
    return dummy_users


@router.post("", response_model=OptimizationOutput)
async def optimize_rides_endpoint(input_data: OptimizationInput) -> OptimizationOutput:
    """
    Optimize a batch of ride requests.
    
    Takes multiple ride requests and produces optimized ride bundles
    that can be consumed by AI agents for bidding and blockchain
    contracts for auction/escrow.
    
    - **ride_requests**: List of ride requests with pickup/drop locations,
      preferred times, and flexibility buffers
      
    Returns optimized bundles with routes, pricing, and time windows.
    """
    try:
        # Validate we have ride requests
        if not input_data.ride_requests:
            raise HTTPException(
                status_code=400,
                detail="At least one ride request is required"
            )
        
        # Get the first user's ride to use as reference for generating dummy users
        user_ride = input_data.ride_requests[0]
        
        # Generate 20 dummy users dynamically based on user's route
        dynamic_dummy_users = generate_dynamic_dummy_users(
            user_pickup=user_ride.pickup,
            user_dropoff=user_ride.dropoff,
            user_time_window=user_ride.time_window,
            count=20
        )
        
        # Combine user rides with dynamically generated dummy rides
        all_rides = list(input_data.ride_requests) + dynamic_dummy_users
        
        # Log the combined request for debugging
        print(f"Optimizing {len(input_data.ride_requests)} user ride(s) + {len(dynamic_dummy_users)} dynamic dummy ride(s) = {len(all_rides)} total")
        print(f"Bounding circle center: ({(user_ride.pickup.latitude + user_ride.dropoff.latitude)/2:.4f}, {(user_ride.pickup.longitude + user_ride.dropoff.longitude)/2:.4f})")
        
        # Call the optimization service with all rides
        result = optimize_rides(all_rides)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Optimization failed: {str(e)}"
        )
