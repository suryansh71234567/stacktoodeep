# Ride Optimization Platform

## 🏗️ GitHub Repository Structure
```
ride-optimization-platform/
│
├── frontend/                          # Team Member 1
│   ├── src/
│   │   ├── components/
│   │   │   ├── RideRequestForm.tsx
│   │   │   ├── MapDisplay.tsx
│   │   │   ├── DiscountCalculator.tsx
│   │   │   └── BiddingVisualization.tsx
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── styles/
│   ├── public/
│   ├── package.json
│   └── README.md
│
├── backend/                           # Team Member 2 (YOU)
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Configuration
│   │   │
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── rides.py             # POST /rides, GET /rides/{id}
│   │   │   ├── optimize.py          # POST /optimize
│   │   │   ├── drivers.py           # Driver endpoints
│   │   │   └── health.py            # Health check
│   │   │
│   │   ├── models/                   # Pydantic models (data schemas)
│   │   │   ├── __init__.py
│   │   │   ├── ride.py              # RideRequest, RideResponse
│   │   │   ├── optimization.py      # OptimizationInput, OptimizationOutput
│   │   │   ├── route.py             # VehicleRoute, Stop
│   │   │   └── pricing.py           # PricingBreakdown
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── optimization/        # YOUR MAIN WORK HERE ⭐
│   │   │   │   ├── __init__.py
│   │   │   │   ├── optimizer.py     # Main optimization orchestrator
│   │   │   │   ├── pooling.py       # Ride matching logic
│   │   │   │   ├── routing.py       # Route calculation (OSRM integration)
│   │   │   │   ├── solver.py        # OR-Tools implementation
│   │   │   │   └── utils.py         # Helper functions
│   │   │   │
│   │   │   ├── discount_calculator.py
│   │   │   ├── pricing_engine.py
│   │   │   └── driver_matcher.py
│   │   │
│   │   ├── db/                       # Database
│   │   │   ├── __init__.py
│   │   │   ├── session.py           # DB connection
│   │   │   └── models.py            # SQLAlchemy models
│   │   │
│   │   └── utils/
│   │       ├── geocoding.py         # Address ↔ coordinates
│   │       ├── time_windows.py      # Time constraint helpers
│   │       └── validation.py        # Input validation
│   │
│   ├── tests/
│   │   ├── test_optimization.py     # YOUR TESTS
│   │   ├── test_api.py
│   │   └── fixtures/
│   │       └── sample_rides.json    # Test data
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── blockchain/                        # Team Member 3
│   ├── contracts/
│   │   ├── RideAuction.sol
│   │   ├── ReputationNFT.sol
│   │   └── PaymentEscrow.sol
│   ├── scripts/
│   │   ├── deploy.js
│   │   └── interact.js
│   ├── test/
│   ├── hardhat.config.js
│   └── README.md
│
├── ai-agent/                          # Team Member 4
│   ├── src/
│   │   ├── negotiator.py
│   │   ├── bidding_strategy.py
│   │   └── prompts/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
│
├── shared/                            # Shared code/types
│   ├── types/
│   │   ├── ride.types.ts           # TypeScript types
│   │   └── ride_schema.json        # JSON schema for validation
│   └── utils/
│
├── docs/
│   ├── API.md                        # API documentation
│   ├── ARCHITECTURE.md               # System architecture
│   └── DEMO_SCRIPT.md                # Demo walkthrough
│
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions CI/CD
│
├── docker-compose.yml                # Run entire stack locally
├── .gitignore
├── README.md                         # Main project README
└── LICENSE
```
