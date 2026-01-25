"""
Demo Auction Simulator

Runs a simulated auction on the real blockchain with artificial delays
to make it visible for hackathon demo purposes.
"""
import asyncio
import secrets
import logging
from typing import Optional, Callable, Any, Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from web3 import Web3
from eth_account import Account

from .demo_companies import DEMO_COMPANIES, DemoCompany, get_company_by_address

logger = logging.getLogger(__name__)


class DemoPhase(Enum):
    """Demo auction phases."""
    IDLE = "IDLE"
    CREATING = "CREATING"
    COMMIT = "COMMIT"
    REVEAL = "REVEAL"
    FINALIZING = "FINALIZING"
    PAYMENT = "PAYMENT"
    COMPLETED = "COMPLETED"


@dataclass
class DemoBid:
    """Represents a bid in the demo."""
    company: DemoCompany
    amount_eth: float
    salt: bytes
    commitment_hash: bytes
    is_revealed: bool = False
    reveal_order: int = 0


@dataclass
class DemoAuctionState:
    """Current state of the demo auction."""
    phase: DemoPhase = DemoPhase.IDLE
    bundle_id: str = ""
    bundle_hash: Optional[bytes] = None
    bids: List[DemoBid] = field(default_factory=list)
    winner: Optional[DemoCompany] = None
    winning_bid_eth: float = 0.0
    payment_tx_hash: str = ""
    error: Optional[str] = None
    
    # Timestamps for UI
    phase_started_at: Optional[datetime] = None
    commit_end_time: Optional[datetime] = None
    reveal_end_time: Optional[datetime] = None


class DemoAuctionSimulator:
    """
    Simulates a blockchain auction with real contract calls and artificial delays.
    
    This is for demo purposes only - it uses hardcoded test keys.
    """
    
    def __init__(self, rpc_url: str, ride_auction_address: str, payment_executor_address: str, admin_private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.ride_auction_address = Web3.to_checksum_address(ride_auction_address)
        self.payment_executor_address = Web3.to_checksum_address(payment_executor_address)
        self.admin_account = Account.from_key(admin_private_key)
        
        # State
        self.state = DemoAuctionState()
        self._event_callback: Optional[Callable[[str, Any], None]] = None
        self._is_running = False
        
        # ABIs (minimal for demo)
        self.ride_auction_abi = [
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "createAuction", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}, {"name": "bidHash", "type": "bytes32"}], "name": "commitBid", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}, {"name": "quotedCostScaled", "type": "uint256"}, {"name": "salt", "type": "bytes32"}], "name": "revealBid", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "finalizeAuction", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "getAuction", "outputs": [
                {"name": "commitStartTime", "type": "uint256"}, {"name": "commitEndTime", "type": "uint256"},
                {"name": "revealEndTime", "type": "uint256"}, {"name": "finalized", "type": "bool"},
                {"name": "winner", "type": "address"}, {"name": "winningBid", "type": "uint256"}, {"name": "bidCount", "type": "uint256"}
            ], "stateMutability": "view", "type": "function"},
        ]
        
        self.payment_executor_abi = [
            {"inputs": [
                {"name": "bundleHash", "type": "bytes32"}, {"name": "winner", "type": "address"},
                {"name": "amountPaidScaled", "type": "uint256"}, {"name": "txHash", "type": "bytes32"}
            ], "name": "recordPayment", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        ]
        
        self.auction_contract = self.w3.eth.contract(address=self.ride_auction_address, abi=self.ride_auction_abi)
        self.payment_contract = self.w3.eth.contract(address=self.payment_executor_address, abi=self.payment_executor_abi)
    
    def set_event_callback(self, callback: Callable[[str, Any], None]):
        """Set callback for real-time event broadcasting."""
        self._event_callback = callback
    
    def _emit(self, event_type: str, data: Any = None):
        """Emit event to connected clients."""
        if self._event_callback:
            self._event_callback(event_type, data)
        logger.info(f"[DEMO] Event: {event_type} - {data}")
    
    def _send_tx(self, func_call, account):
        """Send transaction from specified account."""
        nonce = self.w3.eth.get_transaction_count(account.address)
        tx = func_call.build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })
        signed = self.w3.eth.account.sign_transaction(tx, private_key=account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)
    
    def _advance_time(self, seconds: int):
        """Advance blockchain time (Hardhat only)."""
        self.w3.provider.make_request("evm_increaseTime", [seconds])
        self.w3.provider.make_request("evm_mine", [])
    
    async def run_demo(self, demo_speed: float = 1.0):
        """
        Run a complete demo auction cycle.
        
        Args:
            demo_speed: Speed multiplier (1.0 = normal delays, 2.0 = twice as fast)
        """
        def delay(seconds: float):
            return asyncio.sleep(seconds / demo_speed)
        
        self._is_running = True
        self.state = DemoAuctionState()
        
        try:
            # ===== PHASE 1: CREATE AUCTION =====
            self.state.phase = DemoPhase.CREATING
            self.state.phase_started_at = datetime.now(timezone.utc)
            self.state.bundle_id = f"demo_bundle_{secrets.token_hex(4)}"
            self.state.bundle_hash = self.w3.keccak(text=self.state.bundle_id)
            
            self._emit("PHASE_CHANGE", {"phase": "CREATING", "bundle_id": self.state.bundle_id})
            await delay(1.5)
            
            # Create auction on blockchain
            self._send_tx(
                self.auction_contract.functions.createAuction(self.state.bundle_hash),
                self.admin_account
            )
            self._emit("AUCTION_CREATED", {"bundle_id": self.state.bundle_id, "bundle_hash": self.state.bundle_hash.hex()})
            await delay(1.0)
            
            # ===== PHASE 2: COMMIT PHASE =====
            self.state.phase = DemoPhase.COMMIT
            self.state.phase_started_at = datetime.now(timezone.utc)
            self._emit("PHASE_CHANGE", {"phase": "COMMIT"})
            
            # Companies submit bids one by one
            for i, company in enumerate(DEMO_COMPANIES):
                if not self._is_running:
                    return
                
                await delay(1.5)
                
                # Generate random bid amount (0.35 - 0.55 ETH)
                bid_eth = round(0.35 + (secrets.randbelow(21) / 100), 2)
                salt = secrets.token_bytes(32)
                amount_scaled = int(bid_eth * 1e18)
                
                # Compute commitment hash
                commitment_hash = self.w3.keccak(
                    self.w3.codec.encode(
                        ['bytes32', 'address', 'uint256', 'bytes32'],
                        [self.state.bundle_hash, company.address, amount_scaled, salt]
                    )
                )
                
                # Submit commitment
                company_account = Account.from_key(company.private_key)
                self._send_tx(
                    self.auction_contract.functions.commitBid(self.state.bundle_hash, commitment_hash),
                    company_account
                )
                
                bid = DemoBid(company=company, amount_eth=bid_eth, salt=salt, commitment_hash=commitment_hash)
                self.state.bids.append(bid)
                
                self._emit("BID_COMMITTED", {
                    "company": company.name,
                    "emoji": company.logo_emoji,
                    "color": company.color,
                    "address": company.address[:10] + "...",
                    "bid_hidden": True
                })
            
            await delay(1.0)
            
            # ===== ADVANCE TIME TO REVEAL PHASE =====
            self._emit("TIME_ADVANCING", {"seconds": 301, "reason": "Moving to reveal phase"})
            await delay(1.0)
            self._advance_time(301)
            self._emit("TIME_ADVANCED", {"new_phase": "REVEAL"})
            
            # ===== PHASE 3: REVEAL PHASE =====
            self.state.phase = DemoPhase.REVEAL
            self.state.phase_started_at = datetime.now(timezone.utc)
            self._emit("PHASE_CHANGE", {"phase": "REVEAL"})
            
            # Companies reveal bids
            for i, bid in enumerate(self.state.bids):
                if not self._is_running:
                    return
                
                await delay(1.2)
                
                amount_scaled = int(bid.amount_eth * 1e18)
                company_account = Account.from_key(bid.company.private_key)
                
                self._send_tx(
                    self.auction_contract.functions.revealBid(self.state.bundle_hash, amount_scaled, bid.salt),
                    company_account
                )
                
                bid.is_revealed = True
                bid.reveal_order = i + 1
                
                self._emit("BID_REVEALED", {
                    "company": bid.company.name,
                    "emoji": bid.company.logo_emoji,
                    "color": bid.company.color,
                    "amount_eth": bid.amount_eth,
                    "reveal_order": bid.reveal_order
                })
            
            await delay(1.0)
            
            # ===== ADVANCE TIME TO FINALIZE =====
            self._emit("TIME_ADVANCING", {"seconds": 121, "reason": "Moving to finalization"})
            await delay(0.8)
            self._advance_time(121)
            
            # ===== PHASE 4: FINALIZE =====
            self.state.phase = DemoPhase.FINALIZING
            self._emit("PHASE_CHANGE", {"phase": "FINALIZING"})
            await delay(1.0)
            
            # Call finalize
            self._send_tx(
                self.auction_contract.functions.finalizeAuction(self.state.bundle_hash),
                self.admin_account
            )
            
            # Get result
            result = self.auction_contract.functions.getAuction(self.state.bundle_hash).call()
            winner_address = result[4]
            winning_bid = result[5]
            
            winner = get_company_by_address(winner_address)
            self.state.winner = winner
            self.state.winning_bid_eth = winning_bid / 1e18
            
            self._emit("WINNER_ANNOUNCED", {
                "company": winner.name if winner else "Unknown",
                "emoji": winner.logo_emoji if winner else "❓",
                "color": winner.color if winner else "#888",
                "address": winner_address,
                "winning_bid_eth": self.state.winning_bid_eth
            })
            
            await delay(2.0)
            
            # ===== PHASE 5: AI PAYMENT =====
            self.state.phase = DemoPhase.PAYMENT
            self._emit("PHASE_CHANGE", {"phase": "PAYMENT"})
            await delay(0.5)
            
            self._emit("AI_AGENT_DETECTING", {"message": "AI Agent detected AuctionFinalized event"})
            await delay(1.0)
            
            self._emit("X402_PAYMENT_INITIATING", {
                "from": "AI Agent",
                "to": winner.name if winner else winner_address,
                "amount_eth": self.state.winning_bid_eth
            })
            await delay(1.5)
            
            # Simulate x402 payment
            mock_x402_tx = secrets.token_bytes(32)
            self._emit("X402_PAYMENT_EXECUTED", {"tx_hash": mock_x402_tx.hex()[:16] + "..."})
            await delay(1.0)
            
            # Record on-chain
            self._emit("RECORDING_PAYMENT", {"message": "Recording payment on PaymentExecutor..."})
            receipt = self._send_tx(
                self.payment_contract.functions.recordPayment(
                    self.state.bundle_hash,
                    winner_address,
                    int(self.state.winning_bid_eth * 1e18),
                    mock_x402_tx
                ),
                self.admin_account
            )
            
            self.state.payment_tx_hash = receipt.transactionHash.hex()
            self._emit("PAYMENT_RECORDED", {
                "tx_hash": self.state.payment_tx_hash,
                "block_number": receipt.blockNumber
            })
            
            # ===== COMPLETE =====
            await delay(1.0)
            self.state.phase = DemoPhase.COMPLETED
            self._emit("PHASE_CHANGE", {"phase": "COMPLETED"})
            self._emit("DEMO_COMPLETE", {
                "winner": winner.name if winner else "Unknown",
                "winning_bid_eth": self.state.winning_bid_eth,
                "payment_tx": self.state.payment_tx_hash
            })
            
        except Exception as e:
            logger.error(f"Demo error: {e}")
            self.state.error = str(e)
            self._emit("ERROR", {"message": str(e)})
        finally:
            self._is_running = False
    
    def stop(self):
        """Stop the running demo."""
        self._is_running = False
    
    def get_state(self) -> Dict:
        """Get current state as dict for API."""
        return {
            "phase": self.state.phase.value,
            "bundle_id": self.state.bundle_id,
            "bundle_hash": self.state.bundle_hash.hex() if self.state.bundle_hash else None,
            "bids": [
                {
                    "company": b.company.name,
                    "emoji": b.company.logo_emoji,
                    "color": b.company.color,
                    "amount_eth": b.amount_eth if b.is_revealed else None,
                    "is_revealed": b.is_revealed
                } for b in self.state.bids
            ],
            "winner": {
                "name": self.state.winner.name,
                "emoji": self.state.winner.logo_emoji,
                "color": self.state.winner.color,
                "address": self.state.winner.address
            } if self.state.winner else None,
            "winning_bid_eth": self.state.winning_bid_eth,
            "payment_tx_hash": self.state.payment_tx_hash,
            "error": self.state.error
        }
