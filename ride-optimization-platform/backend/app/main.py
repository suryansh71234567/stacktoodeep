"""
FastAPI application for the Ride Optimization Platform.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.optimize import router as optimize_router


# Create FastAPI application
app = FastAPI(
    title="Ride Optimization Platform",
    description="""
    Backend optimization service for ride-sharing platform.
    
    This service acts as a broker between riders and drivers/aggregators,
    optimizing rides using time flexibility, pooling, and routing to produce
    optimized Ride Bundles.
    
    These bundles are consumed by:
    - Agentic AI (negotiation & bidding)
    - Blockchain smart contracts (auction & escrow)
    """,
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(optimize_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ride-optimization-platform"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Ride Optimization Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
