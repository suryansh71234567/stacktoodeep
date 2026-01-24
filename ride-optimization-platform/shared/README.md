# Shared Schemas

JSON Schema definitions for cross-component data exchange in the Ride Optimization Platform.

## Schemas

| File | Purpose |
|------|---------|
| `ride_request.schema.json` | Input ride request from users |
| `ride_bundle.schema.json` | **⭐ Primary output** - Optimized bundle for AI/blockchain |
| `bid.schema.json` | Driver/aggregator bids on bundles |
| `negotiation_log.schema.json` | AI agent negotiation events |
| `settlement.schema.json` | Blockchain settlement results |

## Data Flow

```
User Request → Backend Optimizer → RideBundle → AI Agents → Bids → Blockchain → Settlement
```

## Usage

These schemas define contracts between:
- **Backend** → outputs `RideBundle`
- **AI Agents** → consume bundles, produce `Bid` and `NegotiationLog`
- **Blockchain** → consumes bids, produces `Settlement`
