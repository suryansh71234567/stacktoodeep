# Demo Module

This folder contains all files for the hackathon demo experience.

## Backend Files

| File | Description |
|------|-------------|
| `demo_router.py` | REST API + WebSocket for demo control |
| `demo_auction_simulator.py` | Runs simulated auction on real blockchain |
| `demo_companies.py` | Company configuration (names, addresses, keys) |

## Frontend Files (Copy to React app)

| File | Copy To |
|------|---------|
| `frontend/types.js` | `src/hooks/types.js` |
| `frontend/useDemoWebSocket.js` | `src/hooks/useDemoWebSocket.js` |
| `frontend/AuctionDemoPanel.jsx` | `src/components/AuctionDemoPanel.jsx` |

## Quick Start

### 1. Start Hardhat Node

```bash
cd blockchain
npx hardhat node
```

### 2. Deploy Contracts (if needed)

```bash
npx hardhat run scripts/deploy.js --network localhost
```

### 3. Update .env with contract addresses

```env
BLOCKCHAIN_RPC_URL=http://localhost:8545
RIDE_AUCTION_ADDRESS=0x...
PAYMENT_EXECUTOR_ADDRESS=0x...
ADMIN_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

### 4. Start Backend with Demo Routes

```bash
cd backend
uvicorn app.main:app --reload
```

### 5. Access Demo

- **API**: `POST http://localhost:8000/demo/start`
- **WebSocket**: `ws://localhost:8000/demo/ws`
- **React**: Use the `AuctionDemoPanel` component

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/demo/start` | Start auction demo |
| GET | `/demo/status` | Get current state |
| POST | `/demo/stop` | Stop running demo |
| POST | `/demo/reset` | Reset for new run |
| WS | `/demo/ws` | Real-time events |

## WebSocket Events

```json
{ "type": "PHASE_CHANGE", "data": { "phase": "COMMIT" } }
{ "type": "BID_COMMITTED", "data": { "company": "RideShare Alpha", "emoji": "🚗" } }
{ "type": "BID_REVEALED", "data": { "company": "RideShare Alpha", "amount_eth": 0.45 } }
{ "type": "WINNER_ANNOUNCED", "data": { "company": "QuickCab Beta", "winning_bid_eth": 0.42 } }
{ "type": "X402_PAYMENT_EXECUTED", "data": { "tx_hash": "0x..." } }
{ "type": "DEMO_COMPLETE", "data": { "winner": "QuickCab Beta", "payment_tx": "0x..." } }
```

## Integration with main.py

Add to `backend/app/main.py`:

```python
# Demo mode (remove for production)
try:
    from demo.demo_router import router as demo_router
    app.include_router(demo_router)
except ImportError:
    pass
```
