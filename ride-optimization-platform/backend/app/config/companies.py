"""
Whitelisted Companies Configuration.

This module contains the demo companies (drivers/aggregators) that are
pre-approved to participate in ride auctions.

These are Hardhat's default test accounts for local development.
DO NOT USE THESE IN PRODUCTION - they are publicly known!
"""

# Demo Companies for Auction Participation
# Each company can submit bids on ride bundles

DEMO_COMPANIES = [
    {
        "name": "RideShare Alpha",
        "wallet_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        "private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        "description": "Premium ride-sharing service",
        "hardhat_account_index": 1
    },
    {
        "name": "QuickCab Beta",
        "wallet_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "private_key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        "description": "Fast and affordable cab service",
        "hardhat_account_index": 2
    },
    {
        "name": "MetroRides Gamma",
        "wallet_address": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        "private_key": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        "description": "City-wide transportation network",
        "hardhat_account_index": 3
    },
    {
        "name": "CityWheels Delta",
        "wallet_address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        "description": "Urban mobility solutions",
        "hardhat_account_index": 4
    },
]

# Admin account (for creating auctions, whitelisting bidders)
ADMIN_ACCOUNT = {
    "name": "Platform Admin",
    "wallet_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "hardhat_account_index": 0
}

# Helper functions
def get_company_addresses() -> list[str]:
    """Get list of all company wallet addresses."""
    return [c["wallet_address"] for c in DEMO_COMPANIES]

def get_company_by_address(address: str) -> dict | None:
    """Find company by wallet address."""
    for company in DEMO_COMPANIES:
        if company["wallet_address"].lower() == address.lower():
            return company
    return None
