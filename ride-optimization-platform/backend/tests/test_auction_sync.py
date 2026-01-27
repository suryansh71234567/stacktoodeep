"""
Synchronous E2E Auction Test for Hardhat
=========================================
This test bypasses the async AI agent polling to avoid timing issues.
Instead, it directly tests all components in sequence.

DUMMY DATA USED:
- bundle_id: "test_bundle_sync_001"
- bid_amount: 0.5 ETH (500000000000000000 wei)
- salt: keccak256("test_secret_salt")
- admin_pk: Hardhat default account #0 private key
- driver_pk: Hardhat default account #1 private key
"""
import pytest
import json
import secrets
from web3 import Web3

# Hardhat default test accounts (publicly known, DO NOT USE IN PRODUCTION)
ADMIN_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
DRIVER_PK = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

# Test configuration
RPC_URL = "http://localhost:8545"
ARTIFACTS_PATH = "../blockchain/artifacts/src"


def test_complete_auction_flow_synchronous():
    """
    Comprehensive synchronous test of the entire auction-to-payment flow.
    
    Tests:
    1. Contract deployment
    2. Bidder whitelisting
    3. Auction creation
    4. Bid commit (sealed bid)
    5. Time advancement
    6. Bid reveal
    7. Auction finalization
    8. Payment recording (simulating AI agent)
    9. Verification
    """
    # =========================================================================
    # SETUP
    # =========================================================================
    print("\n" + "="*60)
    print("AUCTION E2E TEST - SYNCHRONOUS VERSION")
    print("="*60)
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        pytest.skip("Hardhat node not running at http://localhost:8545")
    
    admin = w3.eth.accounts[0]
    driver = w3.eth.accounts[1]
    
    print(f"\n[SETUP] Admin: {admin}")
    print(f"[SETUP] Driver: {driver}")
    
    # =========================================================================
    # 1. DEPLOY CONTRACTS
    # =========================================================================
    print("\n--- PHASE 1: Contract Deployment ---")
    
    with open(f"{ARTIFACTS_PATH}/RideAuction.sol/RideAuction.json") as f:
        auction_data = json.load(f)
    with open(f"{ARTIFACTS_PATH}/PaymentExecutor.sol/PaymentExecutor.json") as f:
        payment_data = json.load(f)
    
    # Deploy RideAuction
    RideAuction = w3.eth.contract(abi=auction_data['abi'], bytecode=auction_data['bytecode'])
    tx = RideAuction.constructor().transact({'from': admin})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    auction_addr = receipt.contractAddress
    print(f"[DEPLOY] RideAuction: {auction_addr}")
    
    # Deploy PaymentExecutor
    PaymentExecutor = w3.eth.contract(abi=payment_data['abi'], bytecode=payment_data['bytecode'])
    tx = PaymentExecutor.constructor().transact({'from': admin})
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    payment_addr = receipt.contractAddress
    print(f"[DEPLOY] PaymentExecutor: {payment_addr}")
    
    # Get contract instances
    auction = w3.eth.contract(address=auction_addr, abi=auction_data['abi'])
    payment = w3.eth.contract(address=payment_addr, abi=payment_data['abi'])
    
    # =========================================================================
    # 2. ADMIN SETUP
    # =========================================================================
    print("\n--- PHASE 2: Admin Setup ---")
    
    # Whitelist driver as bidder
    tx = auction.functions.addBidder(driver).transact({'from': admin})
    w3.eth.wait_for_transaction_receipt(tx)
    print(f"[ADMIN] Whitelisted driver: {driver}")
    
    # Authorize admin as payment recorder (simulating AI agent)
    tx = payment.functions.authorizeRecorder(admin).transact({'from': admin})
    w3.eth.wait_for_transaction_receipt(tx)
    print(f"[ADMIN] Authorized recorder: {admin}")
    
    # =========================================================================
    # 3. CREATE AUCTION
    # =========================================================================
    print("\n--- PHASE 3: Auction Creation ---")
    
    # DUMMY DATA: Bundle ID
    bundle_id = "test_bundle_sync_001"
    bundle_hash = w3.keccak(text=bundle_id)
    print(f"[AUCTION] Bundle ID: {bundle_id}")
    print(f"[AUCTION] Bundle Hash: {bundle_hash.hex()}")
    
    tx = auction.functions.createAuction(bundle_hash).transact({'from': admin})
    w3.eth.wait_for_transaction_receipt(tx)
    print("[AUCTION] Created successfully")
    
    # =========================================================================
    # 4. COMMIT BID (SEALED)
    # =========================================================================
    print("\n--- PHASE 4: Bid Commitment ---")
    
    # DUMMY DATA: Bid amount and salt
    bid_amount = Web3.to_wei(0.5, 'ether')  # 0.5 ETH
    salt = w3.keccak(text="test_secret_salt")
    
    print(f"[BID] Amount: 0.5 ETH ({bid_amount} wei)")
    print(f"[BID] Salt: {salt.hex()[:16]}...")
    
    # Compute commitment hash
    commit_hash = auction.functions.computeCommitmentHash(
        bundle_hash, driver, bid_amount, salt
    ).call()
    print(f"[BID] Commitment hash: {commit_hash.hex()[:16]}...")
    
    # Submit bid commitment
    tx = auction.functions.commitBid(bundle_hash, commit_hash).transact({'from': driver})
    w3.eth.wait_for_transaction_receipt(tx)
    print("[BID] Committed successfully")
    
    # =========================================================================
    # 5. ADVANCE TIME TO REVEAL PHASE
    # =========================================================================
    print("\n--- PHASE 5: Time Advancement (Commit -> Reveal) ---")
    
    # Advance time by 301 seconds (past 5-minute commit window)
    w3.provider.make_request("evm_increaseTime", [301])
    w3.provider.make_request("evm_mine", [])
    print("[TIME] Advanced 301 seconds")
    print("[TIME] Mined new block")
    
    # =========================================================================
    # 6. REVEAL BID
    # =========================================================================
    print("\n--- PHASE 6: Bid Reveal ---")
    
    tx = auction.functions.revealBid(bundle_hash, bid_amount, salt).transact({'from': driver})
    w3.eth.wait_for_transaction_receipt(tx)
    print("[REVEAL] Bid revealed successfully")
    
    # =========================================================================
    # 7. ADVANCE TIME TO FINALIZATION
    # =========================================================================
    print("\n--- PHASE 7: Time Advancement (Reveal -> Finalize) ---")
    
    # Advance time by 121 seconds (past 2-minute reveal window)
    w3.provider.make_request("evm_increaseTime", [121])
    w3.provider.make_request("evm_mine", [])
    print("[TIME] Advanced 121 seconds")
    print("[TIME] Mined new block")
    
    # =========================================================================
    # 8. FINALIZE AUCTION
    # =========================================================================
    print("\n--- PHASE 8: Auction Finalization ---")
    
    tx = auction.functions.finalizeAuction(bundle_hash).transact({'from': admin})
    w3.eth.wait_for_transaction_receipt(tx)
    
    # Get auction results
    result = auction.functions.getAuction(bundle_hash).call()
    winner = result[4]
    winning_bid = result[5]
    
    print(f"[FINALIZE] Winner: {winner}")
    print(f"[FINALIZE] Winning Bid: {winning_bid} wei ({winning_bid / 1e18} ETH)")
    
    assert winner == driver, "Winner should be the driver"
    assert winning_bid == bid_amount, "Winning bid should match"
    print("[FINALIZE] [OK] Auction finalized correctly!")
    
    # =========================================================================
    # 9. SIMULATE AI AGENT PAYMENT RECORDING
    # =========================================================================
    print("\n--- PHASE 9: AI Agent Payment Recording (Simulated) ---")
    
    # DUMMY DATA: Simulated x402 transaction hash
    mock_tx_hash = secrets.token_bytes(32)
    print(f"[AI] Simulated x402 tx hash: {mock_tx_hash.hex()[:16]}...")
    
    # Record payment on-chain (what AI agent would do)
    tx = payment.functions.recordPayment(
        bundle_hash,
        winner,
        winning_bid,
        mock_tx_hash
    ).transact({'from': admin})
    w3.eth.wait_for_transaction_receipt(tx)
    print("[AI] Payment recorded on-chain")
    
    # =========================================================================
    # 10. VERIFICATION
    # =========================================================================
    print("\n--- PHASE 10: Verification ---")
    
    payment_record = payment.functions.getPayment(bundle_hash).call()
    
    recorded_winner = payment_record[0]
    recorded_amount = payment_record[1]
    recorded_tx_hash = payment_record[2]
    recorded = payment_record[4]
    
    print(f"[VERIFY] Recorded: {recorded}")
    print(f"[VERIFY] Winner: {recorded_winner}")
    print(f"[VERIFY] Amount: {recorded_amount} wei")
    print(f"[VERIFY] TX Hash: {recorded_tx_hash.hex()[:16]}...")
    
    assert recorded == True, "Payment should be recorded"
    assert recorded_winner == driver, "Recorded winner should be driver"
    assert recorded_amount == bid_amount, "Recorded amount should match bid"
    
    print("\\n" + "="*60)
    print("[OK] ALL TESTS PASSED!")
    print("="*60)
    
    # =========================================================================
    # DUMMY DATA SUMMARY
    # =========================================================================
    print("\n--- DUMMY DATA USED ---")
    print(f"  bundle_id:      '{bundle_id}'")
    print(f"  bid_amount:     0.5 ETH ({bid_amount} wei)")
    print(f"  salt:           keccak256('test_secret_salt')")
    print(f"  mock_tx_hash:   Random 32 bytes (simulated x402)")
    print(f"  admin_pk:       Hardhat default #0 (publicly known)")
    print(f"  driver_pk:      Hardhat default #1 (publicly known)")


if __name__ == "__main__":
    test_complete_auction_flow_synchronous()
