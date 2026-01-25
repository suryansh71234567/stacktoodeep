"""
Demo Companies Configuration

These are the whitelisted bidding companies hardcoded in the RideAuction smart contract.
Each company has a Hardhat account for demo purposes.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class DemoCompany:
    """Represents a demo bidding company."""
    name: str
    address: str
    private_key: str  # Hardhat default test keys - NEVER use in production
    logo_emoji: str
    color: str

# Hardhat default account private keys (publicly known, for demo only)
DEMO_COMPANIES: List[DemoCompany] = [
    DemoCompany(
        name="RideShare Alpha",
        address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        private_key="0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        logo_emoji="🚗",
        color="#FF6B6B"  # Red
    ),
    DemoCompany(
        name="QuickCab Beta",
        address="0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        private_key="0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        logo_emoji="🚕",
        color="#4ECDC4"  # Teal
    ),
    DemoCompany(
        name="MetroRides Gamma",
        address="0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        private_key="0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        logo_emoji="🚐",
        color="#45B7D1"  # Blue
    ),
    DemoCompany(
        name="CityWheels Delta",
        address="0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        private_key="0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        logo_emoji="🛺",
        color="#96CEB4"  # Green
    ),
]

# Create lookup by address
COMPANY_BY_ADDRESS: Dict[str, DemoCompany] = {
    c.address.lower(): c for c in DEMO_COMPANIES
}

def get_company_by_address(address: str) -> DemoCompany:
    """Get company info by Ethereum address."""
    return COMPANY_BY_ADDRESS.get(address.lower())
