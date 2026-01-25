"""
Seed Rides API - Endpoint for seeding dummy ride requests.

This module provides:
1. POST /seed-rides - Store dummy ride requests for demo
2. GET /seed-rides - Get current seeded rides
3. DELETE /seed-rides - Clear all seeded rides
"""
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.ride import RideRequest
from app.models.optimization import OptimizationInput


router = APIRouter(tags=["seed-rides"])


# In-memory storage for seeded rides
# This will be imported by the optimize router
_seeded_rides: List[RideRequest] = []


def get_seeded_rides() -> List[RideRequest]:
    """Get the list of seeded dummy rides."""
    return _seeded_rides


def clear_seeded_rides():
    """Clear all seeded rides."""
    global _seeded_rides
    _seeded_rides = []


def add_seeded_rides(rides: List[RideRequest]):
    """Add rides to the seeded pool."""
    global _seeded_rides
    _seeded_rides.extend(rides)


@router.post("/seed-rides")
async def seed_rides(input_data: OptimizationInput):
    """
    Seed dummy ride requests for demo purposes.
    
    These rides will be included in optimization when a user
    submits their ride request from the frontend.
    
    - **ride_requests**: List of dummy ride requests to store
    
    Returns the count of seeded rides.
    """
    try:
        # Add the new rides to storage
        add_seeded_rides(input_data.ride_requests)
        
        return {
            "status": "success",
            "message": f"Seeded {len(input_data.ride_requests)} ride requests",
            "total_seeded_rides": len(_seeded_rides),
            "seeded_user_ids": [r.user_id for r in input_data.ride_requests]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to seed rides: {str(e)}"
        )


@router.get("/seed-rides")
async def get_seeds():
    """
    Get all currently seeded ride requests.
    
    Returns the list of all seeded dummy rides that will be
    included in optimization.
    """
    return {
        "total_seeded_rides": len(_seeded_rides),
        "rides": [
            {
                "user_id": r.user_id,
                "pickup": {"lat": r.pickup.lat, "lng": r.pickup.lng},
                "dropoff": {"lat": r.dropoff.lat, "lng": r.dropoff.lng},
                "preferred_time": r.time_window.preferred.isoformat(),
                "buffer_before_min": r.buffer_before_min,
                "buffer_after_min": r.buffer_after_min
            }
            for r in _seeded_rides
        ]
    }


@router.delete("/seed-rides")
async def clear_seeds():
    """
    Clear all seeded ride requests.
    
    Removes all dummy rides from the pool.
    """
    count = len(_seeded_rides)
    clear_seeded_rides()
    
    return {
        "status": "success",
        "message": f"Cleared {count} seeded ride requests",
        "total_seeded_rides": 0
    }
