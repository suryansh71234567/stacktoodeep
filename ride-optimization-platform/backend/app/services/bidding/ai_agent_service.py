"""
AI Agent Service for autonomous payment settlement.
Monitors blockchain for AuctionFinalized events and executes ETH payments via x402.
"""
import logging
import asyncio
import secrets
from typing import Any, Dict, Optional
from web3 import Web3
from .blockchain_adapter import BlockchainAdapter

logger = logging.getLogger(__name__)

class AiAgentService:
    def __init__(self, adapter: BlockchainAdapter):
        self.adapter = adapter
        self.w3 = adapter.w3
        self.is_running = False
        
        # RideAuction event definition for AuctionFinalized
        self.event_abi = {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "internalType": "bytes32", "name": "bundleHash", "type": "bytes32"},
                {"indexed": True, "internalType": "address", "name": "winner", "type": "address"},
                {"indexed": False, "internalType": "uint256", "name": "quotedCostScaled", "type": "uint256"}
            ],
            "name": "AuctionFinalized",
            "type": "event"
        }

    async def start_monitoring(self, poll_interval: float = 2.0):
        """Background loop to monitor for finalized auctions."""
        self.is_running = True
        logger.info("AI Agent starting monitoring for finalized auctions...")
        
        # Start from latest block
        last_polled_block = self.w3.eth.block_number
        
        while self.is_running:
            try:
                current_block = self.w3.eth.block_number
                if current_block > last_polled_block:
                    # Get logs for AuctionFinalized event
                    event_template = self.w3.eth.contract(
                        address=self.adapter.ride_auction_address, 
                        abi=[self.event_abi]
                    )
                    
                    events = event_template.events.AuctionFinalized.get_logs(
                        fromBlock=last_polled_block + 1,
                        toBlock=current_block
                    )
                    
                    for event in events:
                        await self._process_finalized_event(event)
                    
                    last_polled_block = current_block
                    
            except Exception as e:
                logger.error(f"Error in AI Agent monitoring loop: {e}")
            
            await asyncio.sleep(poll_interval)

    async def _process_finalized_event(self, event: Any):
        """Handle an AuctionFinalized event by triggering settlement."""
        bundle_hash = event.args.bundleHash
        winner = event.args.winner
        quoted_cost_scaled = event.args.quotedCostScaled
        
        logger.info(f"AI Agent detected AuctionFinalized for bundle hash {bundle_hash.hex()}. Winner: {winner}")
        
        if winner == "0x0000000000000000000000000000000000000000":
            logger.info("Auction unsold, skipping settlement.")
            return

        # 1. Execute simulated x402 payment
        # In a real system, this would call an x402 gateway
        tx_hash = await self._execute_x402_payment(winner, quoted_cost_scaled)
        
        # 2. Record payment on-chain
        # We need a reverse mapping of bundle_hash -> bundle_id for our adapter
        # For simulation, we'll use a placeholder or assume the adapter can use the hash.
        # Actually, our adapter's record_payment takes bundle_id and re-hashes it.
        # We'll mock the bundle_id as "bundle_" + hash_prefix for this MVP.
        mock_bundle_id = f"auto_bundle_{bundle_hash.hex()[:8]}"
        
        self.adapter.record_payment(
            bundle_id=mock_bundle_id,
            winner=winner,
            amount_scaled=quoted_cost_scaled,
            offchain_tx_hash=tx_hash
        )
        logger.info(f"Settlement recorded for {winner} with amount {quoted_cost_scaled}")

    async def _execute_x402_payment(self, recipient: str, amount_scaled: int) -> bytes:
        """Simulate ETH payment via x402 protocol."""
        eth_amount = amount_scaled / 1e18
        logger.info(f"[SIMULATED x402] Paying {eth_amount} ETH to {recipient}...")
        
        # Mocking a transaction hash
        mock_tx_hash = secrets.token_bytes(32)
        await asyncio.sleep(0.5) # Simulate latency
        return mock_tx_hash

    def stop(self):
        self.is_running = False
