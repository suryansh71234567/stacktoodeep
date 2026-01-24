"""
Rides API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ride import RideRequest, RideRequestCreate, RideStatus
from app.services.ride_service import RideService, RideNotFoundError, RideServiceError

router = APIRouter()

def get_ride_service(db: Session = Depends(get_db)) -> RideService:
    """Dependency to get RideService instance."""
    return RideService(db)

@router.post("/", response_model=RideRequest, status_code=status.HTTP_201_CREATED)
async def create_ride(
    ride_data: RideRequestCreate,
    ride_service: RideService = Depends(get_ride_service)
) -> RideRequest:
    """
    Create a new ride request.
    
    - **pickup**: Pickup location (address or lat/long)
    - **dropoff**: Dropoff location (address or lat/long)
    - **time_window**: Preferred times and flexibility
    - **passengers**: Number of passengers (1-4)
    """
    try:
        return await ride_service.create_ride(ride_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{ride_id}", response_model=RideRequest)
async def get_ride(
    ride_id: str,
    ride_service: RideService = Depends(get_ride_service)
) -> RideRequest:
    """
    Get a specific ride request by ID.
    """
    ride = await ride_service.get_ride(ride_id)
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ride with ID {ride_id} not found"
        )
    return ride

@router.get("/", response_model=List[RideRequest])
async def list_rides(
    user_id: Optional[str] = None,
    status: Optional[RideStatus] = None,
    limit: int = Query(100, ge=1, le=500),
    ride_service: RideService = Depends(get_ride_service)
) -> List[RideRequest]:
    """
    List ride requests with optional filtering.
    """
    try:
        return await ride_service.list_rides(user_id=user_id, status=status, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.patch("/{ride_id}/status", response_model=RideRequest)
async def update_ride_status(
    ride_id: str,
    status_update: dict,  # Expecting {"status": "NEW_STATUS"}
    ride_service: RideService = Depends(get_ride_service)
) -> RideRequest:
    """
    Update the status of a ride request.
    """
    if "status" not in status_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'status' is required"
        )
    
    try:
        new_status = RideStatus(status_update["status"])
        ride = await ride_service.update_ride_status(ride_id, new_status)
        if not ride:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ride with ID {ride_id} not found"
            )
        return ride
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_update['status']}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
