import json
import os
import sys
from web3 import Web3
from eth_account import Account

# Hardhat Default
RPC_URL = "http://127.0.0.1:8545"
PRIVATE_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f5e1476d0930eb" # Account #1 

def load_artifact(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    print("Initializing Web3...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("Failed to connect to blockchain at", RPC_URL)
        sys.exit(1)
    
    account = Account.from_key(PRIVATE_KEY)
    print(f"Deploying from: {account.address}")
    
    # Artifact Paths
    base_path = os.path.join(os.path.dirname(__file__), "..", "blockchain", "artifacts", "src")
    auction_artifact_path = os.path.join(base_path, "RideAuction.sol", "RideAuction.json")
    payment_artifact_path = os.path.join(base_path, "PaymentExecutor.sol", "PaymentExecutor.json")
    
    try:
        # Deploy Auction
        print("Deploying RideAuction...")
        auction_artifact = load_artifact(auction_artifact_path)
        Auction = w3.eth.contract(abi=auction_artifact['abi'], bytecode=auction_artifact['bytecode'])
        
        tx = Auction.constructor().build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        auction_address = receipt.contractAddress
        print(f"RideAuction deployed at: {auction_address}")
        
        # Deploy PaymentExecutor
        print("Deploying PaymentExecutor...")
        payment_artifact = load_artifact(payment_artifact_path)
        Payment = w3.eth.contract(abi=payment_artifact['abi'], bytecode=payment_artifact['bytecode'])
        
        tx = Payment.constructor(auction_address).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        payment_address = receipt.contractAddress
        print(f"PaymentExecutor deployed at: {payment_address}")
        
        # Authorize PaymentExecutor in Auction? Or Authorize AI Agent in PaymentExecutor?
        # Usually PaymentExecutor needs to be authorized to record payments?
        # Read the sol code or assume standard pattern. 
        # For now just output addresses.
        
        return auction_address, payment_address
    except Exception as e:
        print(f"DEPLOYMENT ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
