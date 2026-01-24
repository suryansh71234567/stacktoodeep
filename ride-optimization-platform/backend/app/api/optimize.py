"""
Optimization API endpoint.
"""
from fastapi import APIRouter, HTTPException

from app.models.optimization import OptimizationInput, OptimizationOutput
from app.services.optimization.optimizer import optimize_rides


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
        
        # Call the optimization service
        result = optimize_rides(input_data.ride_requests)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Optimization failed: {str(e)}"
        )
