import os
import json
import time
from web3 import Web3

# 1. CONFIGURATION
# Localhost Hardhat Node URL
BLOCKCHAIN_URL = "http://127.0.0.1:8545" 

# *** YOUR DEPLOYED ADDRESS ***
CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_URL))

# 2. ABI (Matches your RideAuction.sol exactly)
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "_maxPrice", "type": "uint256"}],
        "name": "createAuction",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_auctionId", "type": "uint256"}, {"internalType": "bytes32", "name": "_commitment", "type": "bytes32"}],
        "name": "commitBid",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_auctionId", "type": "uint256"}, {"internalType": "uint256", "name": "_price", "type": "uint256"}, {"internalType": "string", "name": "_salt", "type": "string"}],
        "name": "revealBid",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_auctionId", "type": "uint256"}],
        "name": "finalizeAuction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def run_bidding_process(ride_bundle):
    """
    Orchestrates the Auction: Start -> Commit -> Reveal -> Pay
    """
    try:
        if not w3.is_connected():
            print("⚠️ Blockchain offline. Skipping smart contract calls.")
            return _mock_response(ride_bundle)

        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        
        # Use the first account (Account #0) as the Platform Wallet
        backend_acc = w3.eth.accounts[0] 
        
        # 1. START AUCTION (Backend deposits ETH)
        # We deposit 0.1 ETH to cover the ride cost
        max_price_wei = w3.to_wei(0.1, 'ether') 
        print(f"💰 [Blockchain] Starting Auction for Ride {ride_bundle.get('route_id', '???')}...")
        
        tx = contract.functions.createAuction(max_price_wei).transact({
            'from': backend_acc, 
            'value': max_price_wei
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx)
        
        # In a real app, we parse logs to get ID. For demo, we assume ID=1 or incrementing.
        # Since we just deployed, this is likely Auction #1.
        auction_id = 1 

        # 2. SIMULATE DRIVERS (Commit Phase)
        print("🚗 [Blockchain] Drivers committing encrypted bids...")
        
        # Driver A (Account #1): Bids 0.08 ETH (Hidden)
        salt_a = "secret_a"
        hash_a = w3.solidity_keccak(['uint256', 'string'], [w3.to_wei(0.08, 'ether'), salt_a])
        contract.functions.commitBid(auction_id, hash_a).transact({'from': w3.eth.accounts[1]})

        # Driver B (Account #2): Bids 0.06 ETH (Hidden - This should win)
        salt_b = "secret_b"
        hash_b = w3.solidity_keccak(['uint256', 'string'], [w3.to_wei(0.06, 'ether'), salt_b])
        contract.functions.commitBid(auction_id, hash_b).transact({'from': w3.eth.accounts[2]})

        # 3. REVEAL PHASE
        print("🔓 [Blockchain] Drivers revealing prices...")
        contract.functions.revealBid(auction_id, w3.to_wei(0.08, 'ether'), salt_a).transact({'from': w3.eth.accounts[1]})
        contract.functions.revealBid(auction_id, w3.to_wei(0.06, 'ether'), salt_b).transact({'from': w3.eth.accounts[2]})

        # 4. FINALIZE & PAY
        print("🏆 [Blockchain] Finalizing and Paying Winner via ETH...")
        contract.functions.finalizeAuction(auction_id).transact({'from': backend_acc})

        # 5. GENERATE COUPON
        return {
            "status": "success",
            "winner_address": w3.eth.accounts[2],
            "final_price_eth": 0.06,
            "coupon_code": f"COUPON-{ride_bundle.get('route_id', 'GEN')}-0xETH"
        }

    except Exception as e:
        print(f"❌ Blockchain Error: {e}")
        return _mock_response(ride_bundle)

def _mock_response(ride_bundle):
    return {
        "status": "simulated",
        "tx_hash": "0xsimulated_hash_12345",
        "winner": "Mock Driver",
        "coupon": f"COUPON-{ride_bundle.get('route_id', '000')}"
    }