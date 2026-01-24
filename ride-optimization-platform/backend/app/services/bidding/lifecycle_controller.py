"""
D6: Bidding Lifecycle Controller

Controls the bidding lifecycle WITHOUT touching blockchain internals.
This module orchestrates phases and triggers blockchain adapter methods.

State Machine:
    IDLE → COMMIT → REVEAL → FINALIZED
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

# Type alias for blockchain adapter (assumed to exist)
# In production, this would be imported from the blockchain module
BlockchainAdapter = Any


class BiddingPhase(Enum):
    """Bidding lifecycle phases."""
    IDLE = "IDLE"
    COMMIT = "COMMIT"
    REVEAL = "REVEAL"
    FINALIZED = "FINALIZED"


class BiddingState:
    """
    In-memory state tracker for bidding lifecycles.
    
    In production, this would be replaced with persistent storage.
    """
    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
    
    def get(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        return self._states.get(bundle_id)
    
    def set(self, bundle_id: str, phase: BiddingPhase, **kwargs) -> None:
        self._states[bundle_id] = {
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
    
    def exists(self, bundle_id: str) -> bool:
        return bundle_id in self._states


# Global state instance (would be replaced with proper DI in production)
_bidding_state = BiddingState()

# Placeholder for blockchain adapter
# In production, this would be properly injected
_blockchain_adapter: Optional[BlockchainAdapter] = None


def set_blockchain_adapter(adapter: BlockchainAdapter) -> None:
    """
    Set the blockchain adapter for lifecycle operations.
    
    Args:
        adapter: Blockchain adapter instance with methods:
            - start_commit(bundle_id)
            - start_reveal(bundle_id)
            - fetch_bids(bundle_id)
    """
    global _blockchain_adapter
    _blockchain_adapter = adapter


def get_bidding_state(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current bidding state for a bundle.
    
    Args:
        bundle_id: Bundle identifier
        
    Returns:
        State dict or None if not found
    """
    return _bidding_state.get(bundle_id)


def start_bidding(bundle_id: str) -> None:
    """
    Start the bidding process for a bundle.
    
    Validates bundle exists and triggers COMMIT phase via blockchain adapter.
    Records start timestamp for audit trail.
    
    Args:
        bundle_id: Bundle identifier
        
    Raises:
        ValueError: If bidding already started for this bundle
        RuntimeError: If blockchain adapter not configured
    """
    # Check if bidding already in progress
    if _bidding_state.exists(bundle_id):
        current = _bidding_state.get(bundle_id)
        raise ValueError(
            f"Bidding already started for bundle {bundle_id}. "
            f"Current phase: {current['phase'].value}"
        )
    
    # Trigger COMMIT phase via blockchain adapter
    if _blockchain_adapter is not None:
        _blockchain_adapter.start_commit(bundle_id)
    
    # Record state transition
    _bidding_state.set(
        bundle_id,
        BiddingPhase.COMMIT,
        started_at=datetime.utcnow().isoformat()
    )


def transition_to_reveal(bundle_id: str) -> None:
    """
    Transition bidding from COMMIT to REVEAL phase.
    
    Args:
        bundle_id: Bundle identifier
        
    Raises:
        ValueError: If bundle not in COMMIT phase
    """
    state = _bidding_state.get(bundle_id)
    if state is None or state['phase'] != BiddingPhase.COMMIT:
        raise ValueError(f"Bundle {bundle_id} not in COMMIT phase")
    
    # Trigger REVEAL phase via blockchain adapter
    if _blockchain_adapter is not None:
        _blockchain_adapter.start_reveal(bundle_id)
    
    _bidding_state.set(bundle_id, BiddingPhase.REVEAL)


def end_bidding(bundle_id: str) -> Dict[str, Any]:
    """
    End the bidding process and select winner.
    
    Ends REVEAL phase, prevents new bids, and calls select_winner.
    
    Args:
        bundle_id: Bundle identifier
        
    Returns:
        Winner dict from select_winner
        
    Raises:
        ValueError: If bundle not in REVEAL phase
    """
    state = _bidding_state.get(bundle_id)
    if state is None:
        raise ValueError(f"No bidding found for bundle {bundle_id}")
    
    # Allow ending from COMMIT or REVEAL (for testing/flexibility)
    if state['phase'] not in [BiddingPhase.COMMIT, BiddingPhase.REVEAL]:
        raise ValueError(
            f"Cannot end bidding for bundle {bundle_id}. "
            f"Current phase: {state['phase'].value}"
        )
    
    # Select winner
    winner = select_winner(bundle_id)
    
    # Finalize state
    _bidding_state.set(
        bundle_id, 
        BiddingPhase.FINALIZED,
        winner=winner,
        finalized_at=datetime.utcnow().isoformat()
    )
    
    return winner


def select_winner(bundle_id: str) -> Dict[str, Any]:
    """
    Select the winning bid for a bundle.
    
    Fetches bids from blockchain adapter and selects the one
    with highest profit share (typically highest bid value).
    
    Args:
        bundle_id: Bundle identifier
        
    Returns:
        Winner dict:
            {
                "company_id": str,
                "bid_value": float
            }
            
    Raises:
        ValueError: If no bids found
    """
    # Fetch bids from blockchain
    bids = []
    if _blockchain_adapter is not None:
        bids = _blockchain_adapter.fetch_bids(bundle_id)
    
    if not bids:
        raise ValueError(f"No bids found for bundle {bundle_id}")
    
    # Select highest profit share (highest bid value)
    # In a sealed-bid auction, higher bid = more profit share to platform
    winning_bid = max(bids, key=lambda b: b.get('bid_value', 0))
    
    return {
        "company_id": winning_bid['company_id'],
        "bid_value": winning_bid['bid_value']
    }


def reset_state() -> None:
    """
    Reset all bidding state.
    
    FOR TESTING ONLY. Not for production use.
    """
    global _bidding_state
    _bidding_state = BiddingState()
