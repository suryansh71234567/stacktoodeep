"""
Optimize API endpoint.
POST /optimize - Accepts ride requests and returns optimized bundles.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.ride_request import RideRequest
from app.models.ride_bundle import RideBundle
from app.services.optimization_engine import optimize_ride_requests
from app.services.bundle_builder import build_bundle


router = APIRouter()


class OptimizeRequest(BaseModel):
    """Request body for /optimize endpoint."""
    ride_requests: List[RideRequest]


class OptimizeResponse(BaseModel):
    """Response body for /optimize endpoint."""
    bundles: List[RideBundle]


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_rides(request: OptimizeRequest) -> OptimizeResponse:
    """
    Optimize a list of ride requests into bundles.
    
    Flow:
    1. Validate input (handled by Pydantic)
    2. Optimize/cluster ride requests into pools
    3. Build RideBundle for each pool
    4. Return list of bundles
    
    Args:
        request: OptimizeRequest containing ride_requests
    
    Returns:
        OptimizeResponse containing bundles
    """
    if not request.ride_requests:
        raise HTTPException(status_code=400, detail="No ride requests provided")
    
    # Step 2: Optimize into pools
    pools = optimize_ride_requests(request.ride_requests)
    
    # Step 3: Build bundles
    bundles = [build_bundle(pool) for pool in pools]
    
    # Step 4: Return response
    return OptimizeResponse(bundles=bundles)
