"""
Optimization API endpoint.
"""
from fastapi import APIRouter, HTTPException

from app.models.optimization import OptimizationInput, OptimizationOutput
from app.services.optimization.optimizer import optimize_rides
from app.api.seed_rides import get_seeded_rides


router = APIRouter(prefix="/optimize", tags=["optimization"])


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
        
        # Get seeded dummy rides and combine with user request
        seeded_rides = get_seeded_rides()
        all_rides = list(input_data.ride_requests) + list(seeded_rides)
        
        # Log the combined request for debugging
        print(f"Optimizing {len(input_data.ride_requests)} user ride(s) + {len(seeded_rides)} seeded ride(s) = {len(all_rides)} total")
        
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
