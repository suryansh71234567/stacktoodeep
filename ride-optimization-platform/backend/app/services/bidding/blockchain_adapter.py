"""
Blockchain Adapter for RideAuction and PaymentExecutor.
Handles low-level web3.py calls to the smart contracts.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from web3 import Web3
from eth_account import Account

logger = logging.getLogger(__name__)

class BlockchainAdapter:
    def __init__(self, rpc_url: str, ride_auction_address: str, payment_executor_address: str, private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.ride_auction_address = Web3.to_checksum_address(ride_auction_address)
        self.payment_executor_address = Web3.to_checksum_address(payment_executor_address)
        self.account = Account.from_key(private_key)
        
        # ABIs (simplified for the adapter's needs)
        self.ride_auction_abi = [
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "createAuction", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "finalizeAuction", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "bundleHash", "type": "bytes32"}], "name": "getAuction", "outputs": [
                {"name": "commitStartTime", "type": "uint256"},
                {"name": "commitEndTime", "type": "uint256"},
                {"name": "revealEndTime", "type": "uint256"},
                {"name": "finalized", "type": "bool"},
                {"name": "winner", "type": "address"},
                {"name": "winningBid", "type": "uint256"},
                {"name": "bidCount", "type": "uint256"}
            ], "stateMutability": "view", "type": "function"}
        ]
        
        self.payment_executor_abi = [
            {"inputs": [
                {"name": "bundleHash", "type": "bytes32"},
                {"name": "winner", "type": "address"},
                {"name": "amountPaidScaled", "type": "uint256"},
                {"name": "txHash", "type": "bytes32"}
            ], "name": "recordPayment", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
        ]
        
        self.auction_contract = self.w3.eth.contract(address=self.ride_auction_address, abi=self.ride_auction_abi)
        self.payment_contract = self.w3.eth.contract(address=self.payment_executor_address, abi=self.payment_executor_abi)

    def _send_transaction(self, func_call):
        """Helper to sign and send transaction."""
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = func_call.build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': 2000000,  # Simple fixed gas for MVP
            'gasPrice': self.w3.eth.gas_price
        })
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def start_commit(self, bundle_id: str) -> str:
        """Call createAuction on-chain."""
        bundle_hash = self.w3.keccak(text=bundle_id)
        logger.info(f"Starting blockchain auction for bundle {bundle_id} (hash: {bundle_hash.hex()})")
        receipt = self._send_transaction(self.auction_contract.functions.createAuction(bundle_hash))
        return receipt.transactionHash.hex()

    def start_reveal(self, bundle_id: str):
        """
        Transition logic. 
        Note: In our Solidity contract, REVEAL phase is time-based.
        This method just ensures time has passed (for local tests) or logs.
        """
        logger.info(f"Transitioning to reveal phase for bundle {bundle_id}")
        # No specific on-chain call needed if timing is strictly enforced by contract,
        # but backend might want to trigger finalization later.

    def finalize_auction(self, bundle_id: str) -> Dict[str, Any]:
        """Call finalizeAuction on-chain and return winner info."""
        bundle_hash = self.w3.keccak(text=bundle_id)
        logger.info(f"Finalizing auction for bundle {bundle_id}")
        self._send_transaction(self.auction_contract.functions.finalizeAuction(bundle_hash))
        
        # Fetch results
        details = self.auction_contract.functions.getAuction(bundle_hash).call()
        return {
            "winner": details[4],
            "winningBid": details[5],
            "finalized": details[3]
        }

    def record_payment(self, bundle_id: str, winner: str, amount_scaled: int, offchain_tx_hash: bytes) -> str:
        """Record off-chain payment success on-chain."""
        bundle_hash = self.w3.keccak(text=bundle_id)
        logger.info(f"Recording payment for {bundle_id} to {winner}")
        receipt = self._send_transaction(
            self.payment_contract.functions.recordPayment(
                bundle_hash, 
                Web3.to_checksum_address(winner), 
                amount_scaled, 
                offchain_tx_hash
            )
        )
        return receipt.transactionHash.hex()
