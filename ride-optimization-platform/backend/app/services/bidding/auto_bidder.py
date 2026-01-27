"""
Auto Bidder Service
Simulates automated bidding behavior for the demo.
"""
import asyncio
import logging
import secrets
from typing import Dict, Any, List
from datetime import datetime, timezone
from eth_account import Account
from web3 import Web3

from app.services.bidding.blockchain_adapter import BlockchainAdapter
from demo.demo_companies import DEMO_COMPANIES

logger = logging.getLogger(__name__)

class AutoBidder:
    def __init__(self, adapter: BlockchainAdapter):
        self.adapter = adapter
        self.w3 = adapter.w3
        self.is_running = False
        
    async def run_automation(self, bundle_id: str):
        """
        Run the full automated bidding cycle for a bundle.
        """
        logger.info(f"[AUTO] Starting automation for bundle {bundle_id}")
        
        try:
            # 1. COMMIT PHASE
            # Wait a moment for auction to be fully established
            await asyncio.sleep(2)
            
            bundle_hash = self.w3.keccak(text=bundle_id)
            logger.info(f"[AUTO] Committing bids for {bundle_id}")
            
            bids = []
            
            # Submit bids for each company
            for company in DEMO_COMPANIES:
                # Random bid amount between 0.35 and 0.55 ETH
                bid_eth = round(0.35 + (secrets.randbelow(21) / 100), 2)
                salt = secrets.token_bytes(32)
                amount_scaled = int(bid_eth * 1e18)
                
                # Compute commitment hash
                commitment_hash = self.w3.keccak(
                    self.w3.codec.encode(
                        ['bytes32', 'address', 'uint256', 'bytes32'],
                        [bundle_hash, company.address, amount_scaled, salt]
                    )
                )
                
                # Sign and send transaction
                # We need a separate method for sending from Arbitrary Account
                # Adapter normally uses Admin account. We'll use w3 directly here for simplicity
                # or extend adapter. Let's use w3 directly.
                
                await self._submit_bid(company, bundle_hash, commitment_hash)
                
                bids.append({
                    "company": company,
                    "amount_scaled": amount_scaled,
                    "salt": salt,
                    "bid_eth": bid_eth
                })
                
                logger.info(f"[AUTO] Bid committed: {company.name} ({bid_eth} ETH)")
                await asyncio.sleep(1) # Stagger bids
            
            # 2. WAIT FOR REVEAL PHASE
            # In a real contract, we'd wait for time. 
            # In demo, we might need to "warp" time if configured, 
            # or just assume the backend acts as timekeeper.
            # Let's wait 5 seconds then assume we can reveal (if local network)
            logger.info("[AUTO] Waiting for Reveal Phase...")
            await asyncio.sleep(5)
            
            # If using Hardhat, we might need to advance time
            if "localhost" in self.w3.provider.endpoint_uri or "127.0.0.1" in self.w3.provider.endpoint_uri:
                 try:
                     self.w3.provider.make_request("evm_increaseTime", [300]) # +5 mins
                     self.w3.provider.make_request("evm_mine", [])
                     logger.info("[AUTO] Time advanced by 5 minutes")
                 except Exception:
                     logger.warning("[AUTO] Failed to advance time (might not be hardhat node)")
            
            # 3. REVEAL BIDS
            logger.info(f"[AUTO] Revealing bids for {bundle_id}")
            for bid in bids:
                await self._reveal_bid(bid["company"], bundle_hash, bid["amount_scaled"], bid["salt"])
                logger.info(f"[AUTO] Bid revealed: {bid['company'].name}")
                await asyncio.sleep(1)
                
            # 4. FINALIZE
            logger.info("[AUTO] Finalizing auction...")
            await asyncio.sleep(2)
            
            # Advance time again for reveal end
            if "localhost" in self.w3.provider.endpoint_uri:
                 self.w3.provider.make_request("evm_increaseTime", [120]) # +2 mins
                 self.w3.provider.make_request("evm_mine", [])
            
            # Trigger finalization via Adapter (Admin)
            result = self.adapter.finalize_auction(bundle_id)
            winner = result.get("winner")
            logger.info(f"[AUTO] Auction finalized. Winner: {winner}")
            
            # 5. PAYMENT (Handled by AI Agent Service listening to events)
            # We don't need to do anything here, the AiAgentService should pick it up.
            
            logger.info(f"[AUTO] Automation complete for {bundle_id}")
            
        except Exception as e:
            logger.error(f"[AUTO] Automation failed: {e}")
            import traceback
            traceback.print_exc()

    async def _submit_bid(self, company, bundle_hash, commitment_hash):
        account = Account.from_key(company.private_key)
        # Assuming we need to construct tx manually since adapter uses admin key
        contract_address = self.adapter.ride_auction_address
        contract = self.adapter.auction_contract
        
        tx = contract.functions.commitBid(bundle_hash, commitment_hash).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, private_key=account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    async def _reveal_bid(self, company, bundle_hash, amount_scaled, salt):
        account = Account.from_key(company.private_key)
        contract = self.adapter.auction_contract
        
        tx = contract.functions.revealBid(bundle_hash, amount_scaled, salt).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        
        signed = self.w3.eth.account.sign_transaction(tx, private_key=account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

# Global Instance
_auto_bidder: AutoBidder = None

def get_auto_bidder(adapter: BlockchainAdapter = None) -> AutoBidder:
    global _auto_bidder
    if _auto_bidder is None and adapter:
        _auto_bidder = AutoBidder(adapter)
    return _auto_bidder
