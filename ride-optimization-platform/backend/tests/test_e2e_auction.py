import pytest
import asyncio
import time
from web3 import Web3
from eth_account import Account
from app.services.bidding.blockchain_adapter import BlockchainAdapter
from app.services.bidding.ai_agent_service import AiAgentService
from app.services.bidding import lifecycle_controller

# ABIs and Bytecode (extracted from foundry output)
RIDE_AUCTION_JSON = {
    "abi": [
        {"type":"constructor","inputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"addBidder","inputs":[{"name":"bidder","type":"address"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"commitBid","inputs":[{"name":"bundleHash","type":"bytes32"},{"name":"bidHash","type":"bytes32"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"computeCommitmentHash","inputs":[{"name":"bundleHash","type":"bytes32"},{"name":"bidder","type":"address"},{"name":"quotedCostScaled","type":"uint256"},{"name":"salt","type":"bytes32"}],"outputs":[{"name":"hash","type":"bytes32"}],"stateMutability":"pure"},
        {"type":"function","name":"createAuction","inputs":[{"name":"bundleHash","type":"bytes32"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"finalizeAuction","inputs":[{"name":"bundleHash","type":"bytes32"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"getAuction","inputs":[{"name":"bundleHash","type":"bytes32"}],"outputs":[{"name":"commitStartTime","type":"uint256"},{"name":"commitEndTime","type":"uint256"},{"name":"revealEndTime","type":"uint256"},{"name":"finalized","type":"bool"},{"name":"winner","type":"address"},{"name":"winningBid","type":"uint256"},{"name":"bidCount","type":"uint256"}],"stateMutability":"view"},
        {"type":"function","name":"revealBid","inputs":[{"name":"bundleHash","type":"bytes32"},{"name":"quotedCostScaled","type":"uint256"},{"name":"salt","type":"bytes32"}],"outputs":[],"stateMutability":"nonpayable"}
    ],
    "bytecode": "0x608060405234801561000f575f80fd5b505f80546001600160a01b0319163390811782556040519091907f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0908290a36111218061005b5f395ff3fe..." # Truncated for readability in script, will be populated correctly
}

PAYMENT_EXECUTOR_JSON = {
    "abi": [
        {"type":"constructor","inputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"authorizeRecorder","inputs":[{"name":"recorder","type":"address"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"recordPayment","inputs":[{"name":"bundleHash","type":"bytes32"},{"name":"winner","type":"address"},{"name":"amountPaidScaled","type":"uint256"},{"name":"txHash","type":"bytes32"}],"outputs":[],"stateMutability":"nonpayable"},
        {"type":"function","name":"getPayment","inputs":[{"name":"bundleHash","type":"bytes32"}],"outputs":[{"name":"winner","type":"address"},{"name":"amountPaidScaled","type":"uint256"},{"name":"txHash","type":"bytes32"},{"name":"timestamp","type":"uint256"},{"name":"recorded","type":"bool"}],"stateMutability":"view"}
    ],
    "bytecode": "0x608060405234801561000f575f80fd5b505f80546001600160a01b0319163390811782556040519091907f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0908290a36108068061005b5f395ff3fe..." 
}

# Real bytecodes are large, so I'll read them from the files in the test setup
# instead of hardcoding them here for cleaner code.

@pytest.mark.asyncio
async def test_auction_to_ai_payment_flow():
    """
    E2E Test:
    1. Setup local blockchain (Anvil assumed running at :8545).
    2. Deploy contracts.
    3. Register driver (bidder).
    4. Backend: Start bidding (commit).
    5. Driver: Commit bid.
    6. Advance time (Anvil).
    7. Driver: Reveal bid.
    8. Advance time.
    9. Backend: Finalize auction.
    10. AI Agent: Detect event and record payment.
    11. Verify payment record exists.
    """
    # 0. Setup Connection
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    if not w3.is_connected():
        pytest.skip("Anvil node not found at http://localhost:8545")
    
    admin = w3.eth.accounts[0]
    driver = w3.eth.accounts[driver_idx := 1]
    driver_pk = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d" # Anvil default #1
    admin_pk = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" # Anvil default #0
    
    # 1. Deploy Contracts
    import json
    with open("c:/coding vs/stacktoodeep/stacktoodeep/ride-optimization-platform/blockchain/out/RideAuction.sol/RideAuction.json") as f:
        ride_auction_data = json.load(f)
    with open("c:/coding vs/stacktoodeep/stacktoodeep/ride-optimization-platform/blockchain/out/PaymentExecutor.sol/PaymentExecutor.json") as f:
        payment_executor_data = json.load(f)

    # Deploy RideAuction
    RideAuction = w3.eth.contract(abi=ride_auction_data['abi'], bytecode=ride_auction_data['bytecode']['object'])
    tx_hash = RideAuction.constructor().transact({'from': admin})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    ride_auction_addr = receipt.contractAddress

    # Deploy PaymentExecutor
    PaymentExecutor = w3.eth.contract(abi=payment_executor_data['abi'], bytecode=payment_executor_data['bytecode']['object'])
    tx_hash = PaymentExecutor.constructor().transact({'from': admin})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    payment_executor_addr = receipt.contractAddress

    print(f"Contracts deployed: Auction={ride_auction_addr}, Payment={payment_executor_addr}")

    # 2. Setup Adapters and Services
    adapter = BlockchainAdapter(
        rpc_url="http://localhost:8545",
        ride_auction_address=ride_auction_addr,
        payment_executor_address=payment_executor_addr,
        private_key=admin_pk
    )
    lifecycle_controller.set_blockchain_adapter(adapter)
    
    ai_agent = AiAgentService(adapter)
    
    # 3. Whitelist Driver and Authorize AI Agent (admin acts as agent for recordPayment)
    auction_contract = w3.eth.contract(address=ride_auction_addr, abi=ride_auction_data['abi'])
    payment_contract = w3.eth.contract(address=payment_executor_addr, abi=payment_executor_data['abi'])
    
    auction_contract.functions.addBidder(driver).transact({'from': admin})
    payment_contract.functions.authorizeRecorder(admin).transact({'from': admin})
    
    # Start AI Agent monitoring
    monitor_task = asyncio.create_task(ai_agent.start_monitoring(poll_interval=0.1))

    try:
        # 4. START AUCTION (Backend)
        bundle_id = "test_bundle_e2e_001"
        bundle_hash = w3.keccak(text=bundle_id)
        lifecycle_controller.start_bidding(bundle_id)
        print("Auction created via Backend Adapter")

        # 5. COMMIT BID (Driver)
        bid_amount = Web3.to_wei(0.5, 'ether')
        salt = Web3.keccak(text="secret_salt")
        commit_hash = auction_contract.functions.computeCommitmentHash(
            bundle_hash, driver, bid_amount, salt
        ).call()
        
        auction_contract.functions.commitBid(bundle_hash, commit_hash).transact({'from': driver})
        print("Bid committed by Driver")

        # 6. ADVANCE TO REVEAL (Anvil)
        w3.provider.make_request("evm_increaseTime", [301])
        w3.provider.make_request("evm_mine", [])
        
        # 7. REVEAL BID (Driver)
        auction_contract.functions.revealBid(bundle_hash, bid_amount, salt).transact({'from': driver})
        print("Bid revealed by Driver")

        # 8. ADVANCE TO FINALIZATION
        # (Contract allows early finalization if all revealed, but let's be safe)
        w3.provider.make_request("evm_increaseTime", [121])
        w3.provider.make_request("evm_mine", [])

        # 9. FINALIZE (Backend)
        winner_info = lifecycle_controller.end_bidding(bundle_id)
        print(f"Auction finalized. Winner: {winner_info['company_id']}, Bid: {winner_info['bid_value']} ETH")
        
        # 10. WAIT FOR AI AGENT
        # Detection -> x402 Mock -> recordPayment
        await asyncio.sleep(1.0) # Wait for polling and execution
        
        # 11. VERIFY
        payment_record = payment_contract.functions.getPayment(bundle_hash).call()
        assert payment_record[4] == True  # recorded
        assert payment_record[0] == driver # winner
        assert payment_record[1] == bid_amount # amount
        print("SUCCESS: Payment record verified on-chain")

    finally:
        ai_agent.stop()
        await monitor_task
