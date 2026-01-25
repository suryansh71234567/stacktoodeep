# 🔗 Bharat Moves - Blockchain Auction Layer

Trust-minimized, sealed-bid procurement auction for AI-optimized ride bundles.

## Overview

This module implements the on-chain component of the ride auction system:

1. **RideAuction.sol** - Sealed-bid commit-reveal auction with deterministic winner selection
2. **PaymentExecutor.sol** - Off-chain payment recording for audit trail

### Why Blockchain?

- ✅ Enforces sealed bidding via commit-reveal
- ✅ Prevents backend favoritism
- ✅ Ensures deterministic winner selection
- ✅ Provides public auditability

### What Stays Off-Chain?

- ❌ Ride optimization & routes (privacy-sensitive)
- ❌ Passenger identities
- ❌ ETH/INR conversion (requires oracle)
- ❌ Actual ETH payment execution (via x402)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Network | Ethereum Sepolia (testnet) |
| Language | Solidity ^0.8.24 |
| Framework | Foundry (forge, cast, anvil) |
| Decimal Scale | 1e18 (fixed-point) |

---

## Quick Start

### 1. Install Foundry

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### 2. Install Dependencies

```bash
cd blockchain
forge install
```

### 3. Compile Contracts

```bash
forge build
```

### 4. Run Tests

```bash
# All tests
forge test

# With verbosity
forge test -vvv

# Specific test file
forge test --match-path test/RideAuction.t.sol
```

### 5. Run Local Simulation

```bash
# Start local node
anvil

# In another terminal, run lifecycle simulation
forge script script/AuctionLifecycle.s.sol --fork-url http://localhost:8545 --broadcast
```

---

## Auction Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                      AUCTION TIMELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CREATE        COMMIT PHASE (5 min)      REVEAL PHASE (2 min)   │
│    │                                                            │
│    ▼──────────────────────────────▼──────────────────────▼      │
│    │                              │                      │      │
│    │  Companies submit sealed     │  Companies reveal    │      │
│    │  bid commitments             │  bids + salts        │      │
│    │  (hash only)                 │                      │      │
│                                                                 │
│                                              ┌──────────────────┤
│                                              │   FINALIZE       │
│                                              │   Lowest bid     │
│                                              │   wins           │
│                                              └──────────────────┤
└─────────────────────────────────────────────────────────────────┘
```

### Phases

1. **Creation** - Backend calls `createAuction(bundleHash)`
2. **Commit (5 min)** - Bidders call `commitBid(bundleHash, bidHash)`
3. **Reveal (2 min)** - Bidders call `revealBid(bundleHash, cost, salt)`
4. **Finalize** - Anyone calls `finalizeAuction(bundleHash)`

---

## Contracts

### RideAuction.sol

Main auction contract implementing sealed-bid mechanism.

#### Key Functions

| Function | Access | Description |
|----------|--------|-------------|
| `createAuction(bundleHash)` | Owner | Start new auction |
| `commitBid(bundleHash, bidHash)` | Whitelisted | Submit sealed bid |
| `revealBid(bundleHash, cost, salt)` | Any committed | Reveal bid |
| `finalizeAuction(bundleHash)` | Anyone | Determine winner |
| `addBidder(address)` | Owner | Whitelist company |
| `removeBidder(address)` | Owner | Remove company |

#### Events

```solidity
event AuctionCreated(bytes32 indexed bundleHash, uint256 commitEndTime, uint256 revealEndTime);
event BidCommitted(bytes32 indexed bundleHash, address indexed bidder);
event BidRevealed(bytes32 indexed bundleHash, address indexed bidder, uint256 quotedCostScaled);
event AuctionFinalized(bytes32 indexed bundleHash, address indexed winner, uint256 quotedCostScaled);
event AuctionUnsold(bytes32 indexed bundleHash);
```

### PaymentExecutor.sol

Records off-chain payments for audit trail.

#### Key Functions

| Function | Access | Description |
|----------|--------|-------------|
| `recordPayment(bundleHash, winner, amount, txHash)` | Authorized | Log payment |
| `authorizeRecorder(address)` | Owner | Authorize AI agent |
| `getPayment(bundleHash)` | Anyone | Query payment record |

---

## Deployment

### Local (Anvil)

```bash
# Terminal 1: Start local node
anvil

# Terminal 2: Deploy
forge script script/Deploy.s.sol:DeployLocal --fork-url http://localhost:8545 --broadcast
```

### Testnet (Sepolia)

```bash
# Set environment variables
export PRIVATE_KEY=your_private_key
export SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY

# Deploy
forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast --verify
```

---

## Integration Points

### Backend → Blockchain

```python
# After bundle optimization:
bundle_hash = keccak256(bundle_id)
contract.createAuction(bundle_hash)

# After reveal window:
contract.finalizeAuction(bundle_hash)
```

### Blockchain → Agentic AI

```
Monitor: AuctionFinalized event
  │
  ├── Extract: winner, quotedCostScaled
  │
  ├── Convert: quotedCostScaled / 1e18 → ETH
  │
  ├── Execute: ETH payment via x402
  │
  └── Record: contract.recordPayment(...)
```

---

## Testing

### Test Categories

| File | Coverage |
|------|----------|
| `RideAuction.t.sol` | Unit tests for auction logic |
| `PaymentExecutor.t.sol` | Unit tests for payment recording |
| `Integration.t.sol` | End-to-end lifecycle tests |

### Run All Tests

```bash
forge test -vvv
```

### Test Coverage

```bash
forge coverage
```

---

## Security Considerations

- ✅ bundleHash is single-use (prevents replay)
- ✅ Commit-reveal prevents bid sniping
- ✅ Only whitelisted bidders can participate
- ✅ No ETH custody (payments are off-chain)
- ✅ Deterministic winner selection (verifiable)

---

## File Structure

```
blockchain/
├── foundry.toml           # Foundry config
├── src/
│   ├── RideAuction.sol    # Main auction contract
│   └── PaymentExecutor.sol # Payment recording
├── script/
│   ├── Deploy.s.sol       # Deployment script
│   └── AuctionLifecycle.s.sol # Simulation
├── test/
│   ├── RideAuction.t.sol
│   ├── PaymentExecutor.t.sol
│   └── Integration.t.sol
└── README.md
```