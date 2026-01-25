"""
Demo Router - REST API and WebSocket for hackathon demo.

This provides endpoints and WebSocket connection for real-time auction demo.
"""
import os
import asyncio
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from .demo_auction_simulator import DemoAuctionSimulator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])

# Global simulator instance
_simulator: DemoAuctionSimulator = None
_connected_clients: Set[WebSocket] = set()
_demo_task: asyncio.Task = None


def get_simulator() -> DemoAuctionSimulator:
    """Get or create the demo simulator."""
    global _simulator
    if _simulator is None:
        rpc_url = os.getenv("BLOCKCHAIN_RPC_URL", "http://localhost:8545")
        auction_address = os.getenv("RIDE_AUCTION_ADDRESS")
        payment_address = os.getenv("PAYMENT_EXECUTOR_ADDRESS")
        admin_key = os.getenv("ADMIN_PRIVATE_KEY")
        
        if not all([auction_address, payment_address, admin_key]):
            raise HTTPException(
                status_code=503,
                detail="Blockchain not configured. Set RIDE_AUCTION_ADDRESS, PAYMENT_EXECUTOR_ADDRESS, ADMIN_PRIVATE_KEY"
            )
        
        _simulator = DemoAuctionSimulator(
            rpc_url=rpc_url,
            ride_auction_address=auction_address,
            payment_executor_address=payment_address,
            admin_private_key=admin_key
        )
        
        # Set up event broadcasting
        def broadcast_event(event_type: str, data):
            asyncio.create_task(broadcast_to_clients(event_type, data))
        
        _simulator.set_event_callback(broadcast_event)
    
    return _simulator


async def broadcast_to_clients(event_type: str, data):
    """Broadcast event to all connected WebSocket clients."""
    if not _connected_clients:
        return
    
    message = {"type": event_type, "data": data}
    
    disconnected = set()
    for client in _connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        _connected_clients.discard(client)


# =============================================================================
# REST Endpoints
# =============================================================================

class DemoStartRequest(BaseModel):
    """Request to start demo."""
    speed: float = 1.0  # Speed multiplier


class DemoStatusResponse(BaseModel):
    """Demo status response."""
    phase: str
    bundle_id: str = ""
    winner: dict = None
    winning_bid_eth: float = 0.0
    bids_count: int = 0
    is_running: bool = False


@router.post("/start", response_model=DemoStatusResponse)
async def start_demo(request: DemoStartRequest = DemoStartRequest()):
    """
    Start the demo auction simulation.
    
    - **speed**: Speed multiplier (1.0 = normal, 2.0 = 2x faster)
    """
    global _demo_task
    
    simulator = get_simulator()
    
    # Check if already running
    if _demo_task and not _demo_task.done():
        raise HTTPException(status_code=409, detail="Demo already running. Call /demo/reset first.")
    
    # Start demo in background
    _demo_task = asyncio.create_task(simulator.run_demo(demo_speed=request.speed))
    
    return DemoStatusResponse(
        phase="STARTING",
        is_running=True
    )


@router.get("/status", response_model=dict)
async def get_demo_status():
    """Get current demo state."""
    simulator = get_simulator()
    state = simulator.get_state()
    state["is_running"] = _demo_task and not _demo_task.done()
    return state


@router.post("/reset")
async def reset_demo():
    """Stop and reset the demo."""
    global _demo_task, _simulator
    
    if _simulator:
        _simulator.stop()
    
    if _demo_task:
        _demo_task.cancel()
        try:
            await _demo_task
        except asyncio.CancelledError:
            pass
        _demo_task = None
    
    _simulator = None
    
    return {"status": "reset", "message": "Demo reset. Ready for new run."}


@router.post("/stop")
async def stop_demo():
    """Stop the running demo without full reset."""
    if _simulator:
        _simulator.stop()
    
    return {"status": "stopped"}


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time demo updates.
    
    Connect to receive events like:
    - PHASE_CHANGE
    - BID_COMMITTED
    - BID_REVEALED
    - WINNER_ANNOUNCED
    - X402_PAYMENT_EXECUTED
    - DEMO_COMPLETE
    """
    await websocket.accept()
    _connected_clients.add(websocket)
    
    logger.info(f"WebSocket client connected. Total clients: {len(_connected_clients)}")
    
    try:
        # Send current state on connect
        simulator = get_simulator()
        await websocket.send_json({
            "type": "CONNECTED",
            "data": simulator.get_state()
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                
                # Handle client commands
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data == "status":
                    await websocket.send_json({
                        "type": "STATUS",
                        "data": simulator.get_state()
                    })
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _connected_clients.discard(websocket)
        logger.info(f"WebSocket client removed. Total clients: {len(_connected_clients)}")
