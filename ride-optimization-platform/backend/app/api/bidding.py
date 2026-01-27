"""
Bidding API Router for auction lifecycle management.

This module provides HTTP endpoints to control the blockchain auction lifecycle:
- Start auction for a bundle
- Get auction status
- Finalize auction and get winner

The blockchain adapter is initialized at app startup via main.py.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.bidding import lifecycle_controller
from app.services.bidding.lifecycle_controller import BiddingPhase
from app.services.bidding.auto_bidder import get_auto_bidder
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bidding", tags=["bidding"])


# =============================================================================
# Request/Response Models
# =============================================================================

class StartAuctionRequest(BaseModel):
    """Request to start an auction."""
    bundle_id: str


class AuctionStatusResponse(BaseModel):
    """Auction status response."""
    bundle_id: str
    phase: str
    timestamp: Optional[str] = None
    winner: Optional[dict] = None


class FinalizeAuctionResponse(BaseModel):
    """Response after finalizing auction."""
    bundle_id: str
    winner_address: str
    winning_bid_eth: float
    status: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/start", response_model=AuctionStatusResponse)
async def start_auction(request: StartAuctionRequest):
    """
    Start a blockchain auction for a ride bundle.
    
    This creates an auction on-chain with the given bundle_id.
    The auction enters COMMIT phase where drivers can submit sealed bids.
    
    - **bundle_id**: Unique identifier for the ride bundle
    """
    try:
        lifecycle_controller.start_bidding(request.bundle_id)
        state = lifecycle_controller.get_bidding_state(request.bundle_id)
        
        return AuctionStatusResponse(
            bundle_id=request.bundle_id,
            phase=state["phase"].value,
            timestamp=state.get("timestamp")
        )
        # Trigger automated bidding in background
        adapter = lifecycle_controller._blockchain_adapter
        if adapter:
            auto_bidder = get_auto_bidder(adapter)
            asyncio.create_task(auto_bidder.run_automation(request.bundle_id))
            logger.info(f"Started automated bidding for {request.bundle_id}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Blockchain not configured: {e}")
    except Exception as e:
        logger.error(f"Failed to start auction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{bundle_id}", response_model=AuctionStatusResponse)
async def get_auction_status(bundle_id: str):
    """
    Get the current status of an auction.
    
    - **bundle_id**: The bundle identifier to query
    """
    state = lifecycle_controller.get_bidding_state(bundle_id)
    
    if state is None:
        raise HTTPException(
            status_code=404, 
            detail=f"No auction found for bundle {bundle_id}"
        )
    
    return AuctionStatusResponse(
        bundle_id=bundle_id,
        phase=state["phase"].value,
        timestamp=state.get("timestamp"),
        winner=state.get("winner")
    )


@router.post("/finalize/{bundle_id}", response_model=FinalizeAuctionResponse)
async def finalize_auction(bundle_id: str):
    """
    Finalize an auction and determine the winner.
    
    This ends the auction, calls the smart contract to finalize,
    and returns the winning bidder information.
    
    The AI Agent will automatically detect the AuctionFinalized event
    and execute the payment via x402 protocol.
    
    - **bundle_id**: The bundle identifier to finalize
    """
    try:
        winner = lifecycle_controller.end_bidding(bundle_id)
        
        return FinalizeAuctionResponse(
            bundle_id=bundle_id,
            winner_address=winner["company_id"],
            winning_bid_eth=winner["bid_value"],
            status="finalized"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Blockchain error: {e}")
    except Exception as e:
        logger.error(f"Failed to finalize auction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transition-to-reveal/{bundle_id}")
async def transition_to_reveal(bundle_id: str):
    """
    Manually transition auction from COMMIT to REVEAL phase.
    
    Note: In the smart contract, this is time-based. This endpoint
    is for backend state tracking only.
    """
    try:
        lifecycle_controller.transition_to_reveal(bundle_id)
        state = lifecycle_controller.get_bidding_state(bundle_id)
        
        return {
            "bundle_id": bundle_id,
            "phase": state["phase"].value,
            "message": "Transitioned to REVEAL phase"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
