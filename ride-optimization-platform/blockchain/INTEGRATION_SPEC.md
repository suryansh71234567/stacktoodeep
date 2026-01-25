# Off-Chain Integration Specification

This document formally specifies how the **Backend** and **Agentic AI** systems integrate with the blockchain auction layer.

> ⚠️ **NO CODE GENERATION**: Per specification, this document defines interfaces and contracts only. Implementation is handled by respective teams.

---

## 1. Backend Integration

### 1.1 Role

The Backend acts as the **orchestrator** of the auction lifecycle:

- Creates auctions after bundle optimization
- Monitors auction events
- Triggers finalization after reveal window
- Provides bundle metadata to bidders

### 1.2 Contract Addresses (Post-Deployment)

```
RideAuction:     <DEPLOYED_ADDRESS>
PaymentExecutor: <DEPLOYED_ADDRESS>
```

### 1.3 ABI Required

The Backend must import the following ABIs:

```json
// RideAuction.json
{
  "createAuction": {
    "inputs": [{"name": "bundleHash", "type": "bytes32"}],
    "stateMutability": "nonpayable"
  },
  "finalizeAuction": {
    "inputs": [{"name": "bundleHash", "type": "bytes32"}],
    "stateMutability": "nonpayable"
  },
  "getAuction": {
    "inputs": [{"name": "bundleHash", "type": "bytes32"}],
    "outputs": [
      {"name": "commitStartTime", "type": "uint256"},
      {"name": "commitEndTime", "type": "uint256"},
      {"name": "revealEndTime", "type": "uint256"},
      {"name": "finalized", "type": "bool"},
      {"name": "winner", "type": "address"},
      {"name": "winningBid", "type": "uint256"},
      {"name": "bidCount", "type": "uint256"}
    ]
  },
  "addBidder": {
    "inputs": [{"name": "bidder", "type": "address"}],
    "stateMutability": "nonpayable"
  }
}
```

### 1.4 Events to Monitor

| Event | When | Backend Action |
|-------|------|----------------|
| `AuctionCreated(bundleHash, commitEndTime, revealEndTime)` | After `createAuction()` | Log auction start, notify bidders |
| `BidCommitted(bundleHash, bidder)` | During commit phase | Optional: Track participant count |
| `AuctionFinalized(bundleHash, winner, quotedCostScaled)` | After `finalizeAuction()` | Log winner, trigger AI payment |
| `AuctionUnsold(bundleHash)` | If no valid bids | Generate new bundle_id, retry |

### 1.5 Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Receive ride requests from frontend                         │
│     │                                                           │
│  2. Run optimization → Generate bundle (bundle_id)              │
│     │                                                           │
│  3. Compute bundleHash = keccak256(bundle_id)                   │
│     │                                                           │
│  4. Call createAuction(bundleHash)                              │
│     │                                                           │
│  5. Wait for commit window (5 min)                              │
│     │                                                           │
│  6. Wait for reveal window (2 min)                              │
│     │                                                           │
│  7. Call finalizeAuction(bundleHash)                            │
│     │                                                           │
│  8. If winner exists:                                           │
│     │   → Pass (bundleHash, winner, quotedCostScaled) to AI     │
│     │                                                           │
│  9. If unsold:                                                  │
│        → Generate new bundle_id, go to step 3                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.6 bundleHash Generation

```python
# Python (Backend)
from web3 import Web3

def generate_bundle_hash(bundle_id: str) -> bytes:
    """
    Convert bundle_id to bundleHash for on-chain use.
    
    IMPORTANT: bundleHash is single-use forever.
    If auction fails, generate new bundle_id.
    """
    return Web3.keccak(text=bundle_id)
```

### 1.7 Timing Constraints

| Phase | Duration | Backend Action |
|-------|----------|----------------|
| Commit | 300 seconds | Notify bidders, wait |
| Reveal | 120 seconds | Wait for reveals |
| Post-Reveal | - | Call `finalizeAuction()` |

---

## 2. Agentic AI Integration

### 2.1 Role

The Agentic AI is the **payment executor**:

- Monitors `AuctionFinalized` events
- Converts scaled costs to ETH
- Executes ETH payments via x402 protocol
- Records payments on-chain for audit

### 2.2 ABI Required

```json
// PaymentExecutor.json
{
  "recordPayment": {
    "inputs": [
      {"name": "bundleHash", "type": "bytes32"},
      {"name": "winner", "type": "address"},
      {"name": "amountPaidScaled", "type": "uint256"},
      {"name": "txHash", "type": "bytes32"}
    ],
    "stateMutability": "nonpayable"
  }
}
```

### 2.3 Event to Monitor

```solidity
event AuctionFinalized(
    bytes32 indexed bundleHash,
    address indexed winner,
    uint256 quotedCostScaled
);
```

### 2.4 Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC AI WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Subscribe to AuctionFinalized events                        │
│     │                                                           │
│  2. On event:                                                   │
│     │   Extract: bundleHash, winner, quotedCostScaled           │
│     │                                                           │
│  3. Convert to ETH:                                             │
│     │   ethAmount = quotedCostScaled / 1e18                     │
│     │                                                           │
│  4. [OFF-CHAIN] Fetch ETH/INR rate from Chainlink               │
│     │                                                           │
│  5. [OFF-CHAIN] Execute ETH payment via x402 protocol           │
│     │   To: winner address                                      │
│     │   Amount: ethAmount                                       │
│     │                                                           │
│  6. On success:                                                 │
│     │   Call recordPayment(bundleHash, winner, amount, txHash)  │
│     │                                                           │
│  7. On failure:                                                 │
│        Retry with exponential backoff (max 3 attempts)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Decimal Handling

```python
# Convert from scaled to actual ETH
SCALE_FACTOR = 10 ** 18

def scaled_to_eth(scaled_value: int) -> float:
    return scaled_value / SCALE_FACTOR

def eth_to_scaled(eth_value: float) -> int:
    return int(eth_value * SCALE_FACTOR)

# Example:
# quotedCostScaled = 450000000000000000  (0.45 ETH scaled)
# ethAmount = 0.45 ETH
```

### 2.6 x402 Payment Execution

The x402 protocol handles the actual ETH transfer:

```python
# Pseudocode - actual implementation per x402 spec
async def execute_payment(winner: str, eth_amount: float) -> str:
    """
    Execute ETH payment via x402 protocol.
    
    Returns: Transaction hash
    """
    # 1. Create payment request
    payment = x402.PaymentRequest(
        recipient=winner,
        amount=eth_amount,
        currency="ETH",
        network="sepolia"  # or "mainnet"
    )
    
    # 2. Execute
    result = await x402.execute(payment)
    
    # 3. Return tx hash
    return result.transaction_hash
```

### 2.7 Authorization

The AI wallet address must be authorized in PaymentExecutor:

```solidity
// Owner must call:
paymentExecutor.authorizeRecorder(AI_WALLET_ADDRESS);
```

---

## 3. Bidder (Company) Integration

### 3.1 Role

Companies (Uber, Ola, Rapido, etc.) participate as **bidders**:

- Must be whitelisted by contract owner
- Submit sealed bids during commit phase
- Reveal bids during reveal phase

### 3.2 ABI Required

```json
// RideAuction.json (Bidder functions)
{
  "commitBid": {
    "inputs": [
      {"name": "bundleHash", "type": "bytes32"},
      {"name": "bidHash", "type": "bytes32"}
    ],
    "stateMutability": "nonpayable"
  },
  "revealBid": {
    "inputs": [
      {"name": "bundleHash", "type": "bytes32"},
      {"name": "quotedCostScaled", "type": "uint256"},
      {"name": "salt", "type": "bytes32"}
    ],
    "stateMutability": "nonpayable"
  },
  "computeCommitmentHash": {
    "inputs": [
      {"name": "bundleHash", "type": "bytes32"},
      {"name": "bidder", "type": "address"},
      {"name": "quotedCostScaled", "type": "uint256"},
      {"name": "salt", "type": "bytes32"}
    ],
    "outputs": [{"name": "hash", "type": "bytes32"}]
  }
}
```

### 3.3 Bidding Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BIDDER WORKFLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  COMMIT PHASE (5 minutes):                                      │
│  1. Receive bundle details from backend API                     │
│  2. Decide quotedCostScaled (your bid in ETH × 1e18)            │
│  3. Generate random salt (bytes32)                              │
│  4. Compute: bidHash = computeCommitmentHash(...)               │
│  5. Call commitBid(bundleHash, bidHash)                         │
│  6. Store salt securely (needed for reveal)                     │
│                                                                 │
│  REVEAL PHASE (2 minutes):                                      │
│  7. Call revealBid(bundleHash, quotedCostScaled, salt)          │
│                                                                 │
│  POST-AUCTION:                                                  │
│  8. Check if you won: getAuction(bundleHash).winner             │
│  9. If won: Expect payment from AI agent                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Salt Generation

```python
import secrets

def generate_salt() -> bytes:
    """Generate cryptographically secure salt."""
    return secrets.token_bytes(32)
```

---

## 4. Data Flow Summary

```
                    ┌──────────────────┐
                    │    FRONTEND      │
                    │  (User Request)  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    BACKEND       │
                    │ (Optimization)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────────┐  ┌──────────┐
        │ BIDDER 1 │  │  BLOCKCHAIN  │  │ BIDDER 2 │
        │ (Uber)   │  │ (RideAuction)│  │  (Ola)   │
        └────┬─────┘  └──────┬───────┘  └────┬─────┘
             │               │               │
             └───────────────┼───────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   AGENTIC AI     │
                    │ (x402 Payment)   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ PaymentExecutor  │
                    │  (Audit Trail)   │
                    └──────────────────┘
```

---

## 5. Error Handling

### Backend Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `AuctionAlreadyExists` | bundleHash reused | Generate new bundle_id |
| `OnlyOwner` | Non-owner called admin fn | Use owner wallet |

### Bidder Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `BidderNotWhitelisted` | Not authorized | Contact platform owner |
| `CommitPhaseNotActive` | Wrong timing | Wait for correct phase |
| `InvalidCommitmentHash` | Wrong reveal data | Use correct salt/amount |

### AI Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `OnlyAuthorizedRecorder` | Not authorized | Owner must call `authorizeRecorder()` |
| `PaymentAlreadyRecorded` | Duplicate call | Skip - payment already logged |

---

## 6. Security Considerations

1. **Never log salts** - Salts are secrets until reveal phase
2. **Never reuse bundleHash** - Each bundle needs unique hash
3. **Monitor gas prices** - High gas may delay transactions
4. **Validate winner address** - Before executing payment
5. **Use secure RPC** - Avoid public RPC for production
