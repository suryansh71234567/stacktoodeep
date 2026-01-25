"""
Dummy Users Generator Script for Ride Optimization Demo.

Generates 20 dummy users within 30km radius of IIT Roorkee,
all wanting to travel around 5 PM with varying buffer times.

This script:
1. Generates 20 random ride requests
2. Sends them to the backend where they are stored
3. When the demo user submits a request, it gets optimized with these dummy users

Usage:
    python generate_dummy_users.py
"""

import json
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests

# =============================================================================
# Constants
# =============================================================================

# IIT Roorkee coordinates (center point)
IIT_ROORKEE_LAT = 29.8543
IIT_ROORKEE_LNG = 77.8880

# Maximum radius in km
MAX_RADIUS_KM = 30

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000"

# Target time: 5 PM today
TARGET_HOUR = 17  # 5 PM

# Notable places within 30km of IIT Roorkee (for realistic locations)
NEARBY_PLACES = [
    {"name": "IIT Roorkee Main Gate", "lat": 29.8543, "lng": 77.8880},
    {"name": "Roorkee Railway Station", "lat": 29.8700, "lng": 77.8920},
    {"name": "BHEL Haridwar", "lat": 29.8950, "lng": 77.9700},
    {"name": "Haridwar Junction", "lat": 29.9457, "lng": 78.1642},
    {"name": "Har Ki Pauri", "lat": 29.9574, "lng": 78.1690},
    {"name": "Rishikesh", "lat": 30.0869, "lng": 78.2676},
    {"name": "Laksar", "lat": 29.7500, "lng": 78.0100},
    {"name": "Jwalapur", "lat": 29.9367, "lng": 78.1231},
    {"name": "Landhaura", "lat": 29.8200, "lng": 77.9600},
    {"name": "Manglaur", "lat": 29.7900, "lng": 77.8700},
    {"name": "Deoband", "lat": 29.6900, "lng": 77.6800},
    {"name": "Muzaffarnagar", "lat": 29.4700, "lng": 77.7000},
    {"name": "Saharanpur", "lat": 29.9680, "lng": 77.5510},
    {"name": "Sultanpur", "lat": 29.8100, "lng": 77.8200},
    {"name": "Motichur", "lat": 29.9300, "lng": 78.1000},
    {"name": "Kankhal", "lat": 29.9200, "lng": 78.1400},
    {"name": "Patanjali Yogpeeth", "lat": 29.8800, "lng": 78.0800},
    {"name": "SIDCUL Haridwar", "lat": 29.8600, "lng": 78.0400},
    {"name": "Shivalik Nagar", "lat": 29.9100, "lng": 77.9300},
    {"name": "Gurukul Kangri", "lat": 29.9233, "lng": 78.1167},
]


# =============================================================================
# Helper Functions
# =============================================================================

def generate_random_point_in_radius(
    center_lat: float, 
    center_lng: float, 
    radius_km: float
) -> tuple:
    """
    Generate a random point within a given radius of a center point.
    Uses uniform distribution in a circle.
    """
    # Random angle in radians
    angle = random.uniform(0, 2 * math.pi)
    
    # Random radius with sqrt for uniform distribution in circle
    r = radius_km * math.sqrt(random.uniform(0.1, 1))  # Min 10% of radius
    
    # Convert to lat/lng offset (approximate)
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 km * cos(latitude)
    lat_offset = (r * math.cos(angle)) / 111.0
    lng_offset = (r * math.sin(angle)) / (111.0 * math.cos(math.radians(center_lat)))
    
    return (
        round(center_lat + lat_offset, 6),
        round(center_lng + lng_offset, 6)
    )


def get_random_nearby_place() -> Dict[str, Any]:
    """Get a random place from the nearby places list."""
    return random.choice(NEARBY_PLACES)


def generate_ride_time() -> datetime:
    """
    Generate a ride time around 5 PM today.
    Varies ±1 hour from 5 PM (4 PM to 6 PM).
    """
    today = datetime.now().replace(hour=TARGET_HOUR, minute=0, second=0, microsecond=0)
    
    # Random offset: -60 to +60 minutes from 5 PM
    offset_minutes = random.randint(-60, 60)
    
    return today + timedelta(minutes=offset_minutes)


def generate_buffer_times() -> tuple:
    """
    Generate random buffer_before and buffer_after times.
    Returns (buffer_before_min, buffer_after_min)
    """
    # Buffer before: 5-30 minutes
    buffer_before = random.randint(5, 30)
    
    # Buffer after: 10-60 minutes (this is the "patience" slider)
    buffer_after = random.randint(10, 60)
    
    return buffer_before, buffer_after


def generate_user_id(index: int) -> str:
    """Generate a user ID for dummy user."""
    return f"dummy_user_{index:03d}"


# =============================================================================
# Main Generator
# =============================================================================

def generate_dummy_users(count: int = 20) -> List[Dict[str, Any]]:
    """
    Generate a list of dummy ride requests.
    
    Args:
        count: Number of dummy users to generate
        
    Returns:
        List of ride request dictionaries matching backend format
    """
    ride_requests = []
    
    for i in range(count):
        # Generate pickup and dropoff locations
        # 50% chance to use a known place, 50% random point
        if random.random() < 0.5:
            pickup_place = get_random_nearby_place()
            pickup_lat, pickup_lng = pickup_place["lat"], pickup_place["lng"]
        else:
            pickup_lat, pickup_lng = generate_random_point_in_radius(
                IIT_ROORKEE_LAT, IIT_ROORKEE_LNG, MAX_RADIUS_KM
            )
        
        if random.random() < 0.5:
            dropoff_place = get_random_nearby_place()
            dropoff_lat, dropoff_lng = dropoff_place["lat"], dropoff_place["lng"]
        else:
            dropoff_lat, dropoff_lng = generate_random_point_in_radius(
                IIT_ROORKEE_LAT, IIT_ROORKEE_LNG, MAX_RADIUS_KM
            )
        
        # Ensure pickup and dropoff are different
        while (abs(pickup_lat - dropoff_lat) < 0.01 and abs(pickup_lng - dropoff_lng) < 0.01):
            dropoff_lat, dropoff_lng = generate_random_point_in_radius(
                IIT_ROORKEE_LAT, IIT_ROORKEE_LNG, MAX_RADIUS_KM
            )
        
        # Generate times
        preferred_time = generate_ride_time()
        buffer_before, buffer_after = generate_buffer_times()
        
        # Calculate earliest and latest times
        earliest_time = preferred_time - timedelta(minutes=buffer_before)
        latest_time = preferred_time + timedelta(minutes=buffer_after)
        
        # Create ride request matching backend RideRequest model
        ride_request = {
            "user_id": generate_user_id(i + 1),
            "pickup": {
                "latitude": pickup_lat,
                "longitude": pickup_lng,
                "address": f"Location near IIT Roorkee #{i + 1}"
            },
            "dropoff": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng,
                "address": f"Destination #{i + 1}"
            },
            "time_window": {
                "earliest": earliest_time.isoformat(),
                "preferred": preferred_time.isoformat(),
                "latest": latest_time.isoformat()
            },
            "num_passengers": random.randint(1, 3),
            "max_detour_minutes": random.randint(10, 20)
        }
        
        ride_requests.append(ride_request)
        
        print(f"Generated user {i + 1}: {ride_request['user_id']}")
        print(f"  Pickup: ({pickup_lat}, {pickup_lng})")
        print(f"  Dropoff: ({dropoff_lat}, {dropoff_lng})")
        print(f"  Time: {preferred_time.strftime('%H:%M')} (buffer: -{buffer_before}/+{buffer_after} min)")
        print()
    
    return ride_requests


def send_to_backend(ride_requests: List[Dict[str, Any]]) -> Dict:
    """
    Send the generated ride requests to the backend for storage.
    Uses the /seed-rides endpoint.
    """
    url = f"{BACKEND_URL}/seed-rides"
    
    try:
        response = requests.post(
            url,
            json={"ride_requests": ride_requests},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully sent {len(ride_requests)} ride requests to backend")
            return response.json()
        else:
            print(f"❌ Failed to send requests: {response.status_code}")
            print(response.text)
            return {"error": response.text}
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend at {BACKEND_URL}")
        print("   Make sure the backend is running: uvicorn app.main:app --reload --port 8000")
        return {"error": "Connection failed"}


def save_to_file(ride_requests: List[Dict[str, Any]], filename: str = "dummy_rides.json"):
    """Save ride requests to a JSON file for reference."""
    with open(filename, "w") as f:
        json.dump({"ride_requests": ride_requests}, f, indent=2, default=str)
    print(f"💾 Saved to {filename}")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚗 Dummy Users Generator for Ride Optimization Demo")
    print("=" * 60)
    print(f"Center: IIT Roorkee ({IIT_ROORKEE_LAT}, {IIT_ROORKEE_LNG})")
    print(f"Radius: {MAX_RADIUS_KM} km")
    print(f"Target time: Around 5 PM today")
    print("=" * 60)
    print()
    
    # Generate dummy users
    dummy_rides = generate_dummy_users(20)
    
    print("=" * 60)
    print()
    
    # Save to file
    save_to_file(dummy_rides)
    
    # Send to backend
    print()
    print("Sending to backend...")
    result = send_to_backend(dummy_rides)
    
    if "error" not in result:
        print()
        print("=" * 60)
        print("✅ DONE! Dummy users are now in the backend.")
        print("   When you submit a ride from the frontend,")
        print("   it will be optimized together with these users.")
        print("=" * 60)
