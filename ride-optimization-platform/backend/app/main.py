"""
Ride Optimization Broker - FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.optimize import router as optimize_router


app = FastAPI(
    title="Ride Optimization Broker",
    description="Off-chain ride optimization service for pooling and bundling ride requests",
    version="1.0.0",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(optimize_router, tags=["Optimization"])


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ride-optimization-broker"}
