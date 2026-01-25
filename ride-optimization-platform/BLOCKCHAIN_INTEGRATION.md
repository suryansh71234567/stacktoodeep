# Blockchain Auction & AI Payment Integration Guide

> **Purpose**: This document details the blockchain auction and x402 payment system implementation, listing all changes required to integrate with other project components (backend, frontend) that may exist in different branches.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Smart Contracts](#2-smart-contracts)
3. [Backend Integration Points](#3-backend-integration-points)
4. [Frontend Integration Points](#4-frontend-integration-points)
5. [Environment Configuration](#5-environment-configuration)
6. [Auction & Payment Flow](#6-auction--payment-flow)
7. [Test Verification](#7-test-verification)
8. [Cross-Branch Integration Checklist](#8-cross-branch-integration-checklist)

---

## 1. Overview

### What This Branch Contains

| Component | Path | Description |
|-----------|------|-------------|
| RideAuction.sol | `blockchain/src/RideAuction.sol` | Sealed-bid commit-reveal auction |
| PaymentExecutor.sol | `blockchain/src/PaymentExecutor.sol` | x402 payment audit trail |
| BlockchainAdapter | `backend/app/services/bidding/blockchain_adapter.py` | Python ↔ Smart Contract interface |
| AI Agent Service | `backend/app/services/bidding/ai_agent_service.py` | Monitors auctions, executes x402 payments |
| Bidding API | `backend/app/api/bidding.py` | REST endpoints for auction lifecycle |
| Lifecycle Controller | `backend/app/services/bidding/lifecycle_controller.py` | State machine for bidding phases |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RIDE OPTIMIZATION PLATFORM                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   Frontend   │────▶│                   Backend                        │  │
│  │  (React/Vue) │     │  ┌─────────────┐  ┌──────────────────────────┐   │  │
│  └──────────────┘     │  │ Optimization│  │     Bidding Module       │   │  │
│                       │  │   Service   │──│  • lifecycle_controller  │   │  │
│                       │  └─────────────┘  │  • blockchain_adapter    │   │  │
│                       │                   │  • ai_agent_service      │   │  │
│                       │                   └───────────┬──────────────┘   │  │
│                       └───────────────────────────────┼──────────────────┘  │
│                                                       │                     │
│                               ┌───────────────────────┼───────────────────┐ │
│                               │                       ▼                   │ │
│  ┌───────────────────────┐    │   ┌─────────────────────────────────┐    │ │
│  │   Bidding Companies   │◀───│   │        Blockchain Layer         │    │ │
│  │  (Uber, Ola, Rapido)  │────│──▶│  ┌──────────────────────────┐   │    │ │
│  │                       │    │   │  │     RideAuction.sol      │   │    │ │
│  │  • commitBid()        │    │   │  │  • createAuction()       │   │    │ │
│  │  • revealBid()        │    │   │  │  • commitBid()           │   │    │ │
│  └───────────────────────┘    │   │  │  • revealBid()           │   │    │ │
│                               │   │  │  • finalizeAuction()     │   │    │ │
│                               │   │  └──────────────────────────┘   │    │ │
│  ┌───────────────────────┐    │   │  ┌──────────────────────────┐   │    │ │
│  │    Agentic AI         │    │   │  │   PaymentExecutor.sol    │   │    │ │
│  │  (x402 Payment)       │────│──▶│  │  • recordPayment()       │   │    │ │
│  │                       │    │   │  │  • getPayment()          │   │    │ │
│  │  • Monitor events     │    │   │  └──────────────────────────┘   │    │ │
│  │  • Execute payment    │    │   └─────────────────────────────────┘    │ │
│  │  • Record on-chain    │    │                                          │ │
│  └───────────────────────┘    └──────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Smart Contracts

### RideAuction.sol

**Purpose**: Sealed-bid commit-reveal auction for AI-optimized ride bundles

| Function | Caller | Description |
|----------|--------|-------------|
| `createAuction(bundleHash)` | Backend (owner) | Start new auction |
| `addBidder(address)` | Owner | Whitelist a company |
| `commitBid(bundleHash, bidHash)` | Whitelisted bidders | Submit sealed bid |
| `revealBid(bundleHash, amount, salt)` | Bidders | Reveal sealed bid |
| `finalizeAuction(bundleHash)` | Anyone (after reveal) | Determine winner |
| `getAuction(bundleHash)` | Anyone | Query auction state |

**Events Emitted:**
- `AuctionCreated(bundleHash, commitEndTime, revealEndTime)`
- `BidCommitted(bundleHash, bidder)`
- `BidRevealed(bundleHash, bidder, quotedCostScaled)`
- `AuctionFinalized(bundleHash, winner, quotedCostScaled)` ← AI monitors this
- `AuctionUnsold(bundleHash)`

### PaymentExecutor.sol

**Purpose**: Records off-chain ETH payments executed via x402 protocol

| Function | Caller | Description |
|----------|--------|-------------|
| `authorizeRecorder(address)` | Owner | Authorize AI wallet |
| `recordPayment(bundleHash, winner, amount, txHash)` | Authorized recorder | Log payment |
| `getPayment(bundleHash)` | Anyone | Query payment record |
| `isPaymentRecorded(bundleHash)` | Anyone | Check if paid |

---

## 3. Backend Integration Points

### Files to Add/Merge from This Branch

| File | Action | Description |
|------|--------|-------------|
| `app/api/bidding.py` | **NEW** | REST API for auction lifecycle |
| `app/services/bidding/__init__.py` | **NEW** | Bidding module exports |
| `app/services/bidding/blockchain_adapter.py` | **NEW** | Web3 contract interface |
| `app/services/bidding/ai_agent_service.py` | **NEW** | Event monitoring & x402 |
| `app/services/bidding/lifecycle_controller.py` | **NEW** | State machine |
| `app/services/bidding/types.py` | **NEW** | Pydantic models |
| `app/services/bidding/utils.py` | **NEW** | Helper functions |
| `app/services/bidding/pre_bidding_builder.py` | **NEW** | Pre-auction payload |
| `app/services/bidding/post_bidding_distributor.py` | **NEW** | Post-auction distribution |
| `app/main.py` | **MODIFY** | Add bidding router import |
| `tests/test_bidding.py` | **NEW** | Unit tests |
| `tests/test_auction_sync.py` | **NEW** | E2E integration test |

### main.py Changes Required

```python
# Add these imports
from app.api.bidding import router as bidding_router
from app.services.bidding.blockchain_adapter import BlockchainAdapter
from app.services.bidding import lifecycle_controller

# Add lifespan handler to initialize blockchain adapter
@asynccontextmanager
async def lifespan(app: FastAPI):
    rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
    auction_address = os.getenv("RIDE_AUCTION_ADDRESS")
    payment_address = os.getenv("PAYMENT_EXECUTOR_ADDRESS")
    admin_key = os.getenv("ADMIN_PRIVATE_KEY")
    
    if all([rpc_url, auction_address, payment_address, admin_key]):
        adapter = BlockchainAdapter(
            rpc_url=rpc_url,
            ride_auction_address=auction_address,
            payment_executor_address=payment_address,
            private_key=admin_key
        )
        lifecycle_controller.set_blockchain_adapter(adapter)
    yield

# Add router
app.include_router(bidding_router)
```

### API Endpoints Added

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bidding/start` | Start auction for bundle |
| GET | `/bidding/status/{bundle_id}` | Get auction status |
| POST | `/bidding/finalize/{bundle_id}` | Finalize and get winner |
| POST | `/bidding/transition-to-reveal/{bundle_id}` | Manual phase transition |

---

## 4. Frontend Integration Points

### Required Changes in Frontend (Different Branch)

| Component | Changes Needed |
|-----------|---------------|
| **Ride Request Flow** | After optimization, show auction status |
| **Auction Status Display** | Poll `/bidding/status/{bundle_id}` |
| **Winner Display** | Show winning driver/company after finalization |
| **Price Display** | Show winning bid amount to user |

### Suggested API Calls

```javascript
// 1. After ride bundle is created, start auction
const startAuction = async (bundleId) => {
  const response = await fetch('/bidding/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bundle_id: bundleId })
  });
  return response.json();
};

// 2. Poll for auction status
const getAuctionStatus = async (bundleId) => {
  const response = await fetch(`/bidding/status/${bundleId}`);
  return response.json();
  // Returns: { bundle_id, phase, timestamp, winner }
};

// 3. Finalize auction (after reveal period)
const finalizeAuction = async (bundleId) => {
  const response = await fetch(`/bidding/finalize/${bundleId}`, {
    method: 'POST'
  });
  return response.json();
  // Returns: { bundle_id, winner_address, winning_bid_eth, status }
};
```

### Auction Phases for UI

| Phase | Duration | UI State |
|-------|----------|----------|
| `COMMIT` | 5 minutes | "Drivers bidding..." |
| `REVEAL` | 2 minutes | "Verifying bids..." |
| `FINALIZED` | - | "Winner: {company}" |

---

## 5. Environment Configuration

### Required Environment Variables

Add these to `.env`:

```env
# Blockchain Configuration
BLOCKCHAIN_RPC_URL=http://localhost:8545        # or Sepolia RPC
RIDE_AUCTION_ADDRESS=0x...                      # Deployed contract
PAYMENT_EXECUTOR_ADDRESS=0x...                  # Deployed contract
ADMIN_PRIVATE_KEY=0x...                         # Backend wallet (owner)
```

### Contract Deployment

```bash
# Deploy contracts (from blockchain folder)
cd blockchain
npx hardhat run scripts/deploy.js --network localhost

# Output will show deployed addresses - copy to .env
```

---

## 6. Auction & Payment Flow

### Complete E2E Flow

```
1. USER                              2. BACKEND
   │                                    │
   │  Request ride ─────────────────▶   │
   │                                    │
   │                                 Optimize bundle
   │                                    │
   │                                 createAuction(bundleHash)
   │                                    │
   │                                    ▼
                               3. BLOCKCHAIN (RideAuction)
                                        │
                                  ┌─────┴─────┐
                                  │           │
                              4. BIDDERS   5. BIDDERS
                              commitBid()  revealBid()
                                  │           │
                                  └─────┬─────┘
                                        │
                               finalizeAuction()
                                        │
                                        ▼
                               emit AuctionFinalized
                                        │
                                        ▼
                               6. AI AGENT SERVICE
                                        │
                               Detect AuctionFinalized
                                        │
                               Execute x402 Payment
                                        │
                               recordPayment() on PaymentExecutor
                                        │
                                        ▼
                               7. PAYMENT VERIFIED ON-CHAIN
```

### Timing

| Step | Duration |
|------|----------|
| Commit phase | 5 minutes |
| Reveal phase | 2 minutes |
| Finalization | Immediate |
| AI Payment | ~1 second (simulated) |

---

## 7. Test Verification

### Running Tests

```bash
# Unit tests (no blockchain needed)
cd backend
python -m pytest tests/test_bidding.py -v

# E2E tests (requires Hardhat node)
# Terminal 1: Start blockchain
cd blockchain
npx hardhat node

# Terminal 2: Run E2E test
cd backend
python tests/test_auction_sync.py
```

### Test Coverage

| Test File | Coverage |
|-----------|----------|
| `test_bidding.py` | Unit tests for bidding module |
| `test_auction_sync.py` | Full E2E: deploy → bid → reveal → finalize → payment |

### Expected E2E Output

```
============================================================
AUCTION E2E TEST - SYNCHRONOUS VERSION
============================================================
[SETUP] Admin: 0xf39...
[DEPLOY] RideAuction: 0x5Fb...
[DEPLOY] PaymentExecutor: 0xe7f...
[AUCTION] Created successfully
[BID] Committed successfully
[REVEAL] Bid revealed successfully
[FINALIZE] Winner: 0x709...
[AI] Payment recorded on-chain
[VERIFY] Recorded: True
============================================================
[OK] ALL TESTS PASSED!
============================================================
```

---

## 8. Cross-Branch Integration Checklist

### When Merging This Branch

- [ ] **Copy blockchain folder** (`blockchain/src/*.sol`, `blockchain/test/*.sol`)
- [ ] **Copy bidding service** (`backend/app/services/bidding/`)
- [ ] **Copy bidding API** (`backend/app/api/bidding.py`)
- [ ] **Copy tests** (`backend/tests/test_bidding.py`, `test_auction_sync.py`)
- [ ] **Update main.py** with bidding router and lifespan handler
- [ ] **Update requirements.txt** with `web3>=6.0.0`, `eth-account>=0.8.0`
- [ ] **Update .env.example** with blockchain variables
- [ ] **Deploy contracts** and update addresses in .env

### Dependencies to Add

```txt
# Add to requirements.txt
web3>=6.0.0
eth-account>=0.8.0
```

### Frontend Changes (Separate Branch)

- [ ] Add auction status component
- [ ] Add API calls to `/bidding/*` endpoints
- [ ] Show auction phase progress to user
- [ ] Display winning company/driver after finalization

---

## Files in This Implementation

```
ride-optimization-platform/
├── blockchain/
│   ├── src/
│   │   ├── RideAuction.sol          # Sealed-bid auction contract
│   │   └── PaymentExecutor.sol      # Payment audit trail
│   ├── test/
│   │   └── Integration.t.sol        # Foundry tests
│   ├── artifacts/                   # Compiled contracts
│   ├── INTEGRATION_SPEC.md          # Detailed spec
│   └── README.md                    # Blockchain docs
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── bidding.py           # REST endpoints
│   │   ├── services/
│   │   │   └── bidding/
│   │   │       ├── __init__.py
│   │   │       ├── blockchain_adapter.py
│   │   │       ├── ai_agent_service.py
│   │   │       ├── lifecycle_controller.py
│   │   │       ├── types.py
│   │   │       └── utils.py
│   │   └── main.py                  # Updated with bidding router
│   ├── tests/
│   │   ├── test_bidding.py          # Unit tests
│   │   └── test_auction_sync.py     # E2E test
│   └── .env.example                 # Updated with blockchain vars
│
└── BLOCKCHAIN_INTEGRATION.md        # This document
```

---

## 9. Hackathon Demo Module

A complete demo experience is available in `backend/demo/` for showcasing the auction and payment flow in real-time.

### Demo Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HACKATHON DEMO                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  React Frontend                    Python Backend               │
│  ┌─────────────────────┐          ┌─────────────────────┐      │
│  │ AuctionDemoPanel    │◀─────────│ demo_router.py      │      │
│  │ • Phase Timeline    │ WebSocket│ • POST /demo/start  │      │
│  │ • Bid Feed          │ Events   │ • GET /demo/status  │      │
│  │ • Winner Animation  │          │ • WS /demo/ws       │      │
│  │ • Payment Flow      │          └──────────┬──────────┘      │
│  └─────────────────────┘                     │                  │
│                                              ▼                  │
│                              ┌───────────────────────────┐      │
│                              │ demo_auction_simulator.py │      │
│                              │ • Runs REAL blockchain tx │      │
│                              │ • 4 companies bid         │      │
│                              │ • AI Agent pays winner    │      │
│                              └───────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Demo Companies

| Company | Emoji | Address |
|---------|-------|---------|
| RideShare Alpha | 🚗 | `0x7099...79C8` |
| QuickCab Beta | 🚕 | `0x3C44...93BC` |
| MetroRides Gamma | 🚐 | `0x90F7...3906` |
| CityWheels Delta | 🛺 | `0x15d3...6A65` |

### Running the Demo

**1. Start Hardhat node:**
```bash
cd blockchain
npx hardhat node
```

**2. Start backend with demo routes:**

Add to `main.py`:
```python
# Demo mode (remove for production)
try:
    from demo.demo_router import router as demo_router
    app.include_router(demo_router)
except ImportError:
    pass
```

Then run:
```bash
cd backend
uvicorn app.main:app --reload
```

**3. Copy React components to your frontend:**
```
backend/demo/frontend/types.ts          → src/hooks/types.ts
backend/demo/frontend/useDemoWebSocket.ts → src/hooks/useDemoWebSocket.ts
backend/demo/frontend/AuctionDemoPanel.tsx → src/components/AuctionDemoPanel.tsx
```

**4. Use the component:**
```tsx
import { AuctionDemoPanel } from './components/AuctionDemoPanel';

function App() {
  return <AuctionDemoPanel />;
}
```

### WebSocket Events

| Event | Description |
|-------|-------------|
| `PHASE_CHANGE` | Auction phase changed |
| `BID_COMMITTED` | Company submitted sealed bid |
| `BID_REVEALED` | Bid amount revealed |
| `WINNER_ANNOUNCED` | Auction winner declared |
| `X402_PAYMENT_EXECUTED` | AI Agent executed payment |
| `PAYMENT_RECORDED` | On-chain audit recorded |
| `DEMO_COMPLETE` | Demo finished |

### Demo Files

```
backend/demo/
├── __init__.py
├── demo_router.py              # REST API + WebSocket
├── demo_auction_simulator.py   # Simulation logic  
├── demo_companies.py           # Company config
├── README.md                   # Quick start guide
└── frontend/
    ├── types.js                # JavaScript types (or types.ts)
    ├── useDemoWebSocket.js     # React hook (or .ts)
    ├── AuctionDemoPanel.jsx    # React component (or .tsx)
    └── [TypeScript versions also available]
```

To Enable Demo in main.py:
Add after other router includes:

python
try:
    from demo.demo_router import router as demo_router
    app.include_router(demo_router)
except ImportError:
    pass

