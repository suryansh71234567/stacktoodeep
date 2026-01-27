# Ride Optimization Platform 🚖⚡

A decentralized, AI-driven ride optimization and bidding platform.

## 🚀 Key Features
- **AI-Powered Ride Bundling**: Optimizes routes and pools rides for maximum efficiency.
- **Blockchain Auction**: Sealed-bid commit-reveal auctions for ride bundles (`RideAuction.sol`).
- **Automated Bidding Agents**: Autonomous AI agents that bid on auctions (`AutoBidder`).
- **x402 Payment Settlement**: Simulated AI-to-AI payments verified on-chain.

## 🏗️ GitHub Repository Structure
```
ride-optimization-platform/
│
├── frontend/                          # React + TypeScript Frontend
├── backend/                           # FastAPI Backend + Pydantic Models
├── blockchain/                        # Hardhat + Solidity Contracts
├── ai-agent/                          # AI Agent (RL/Negotiation)
├── shared/                            # Shared Types
└── docker-compose.yml                 # (Optional) Container orchestration
```

## 🛠️ Getting Started (Local Development)

### Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- PostgreSQL (running centrally or via Docker)
- Redis (running locally)

### 1. Blockchain Setup
Start the local blockchain node first. This simulates the Ethereum network.

```bash
cd blockchain
npm install
npx hardhat node
```
*Keep this terminal running!*

**Deploy Contracts:**
In a new terminal:
```bash
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
```
*Note: Copy the deployed contract addresses into `backend/.env` if they change.*

### 2. Backend Setup
The backend handles optimization, auction orchestration, and serving the API.

```bash
cd backend
python -m venv venv
# Activate venv: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

**Configuration:**
Ensure `backend/.env` exists (copy `.env.example` if needed) and `BLOCKCHAIN_RPC_URL` points to `http://127.0.0.1:8545`.

**Run Server:**
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
The user interface for requesting rides and viewing demos.

```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

## 🧪 Running the Demo
1. Open the Frontend.
2. Submit a Ride Request.
3. Watch the **Backend Terminal** for:
   - Optimization logs (bundling rides).
   - `[AUTO]` Bidding logs (automated agents bidding on the blockchain).
   - `[AI]` Payment logs (settlement on-chain).
