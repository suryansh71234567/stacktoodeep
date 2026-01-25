"""
FastAPI application for the Ride Optimization Platform.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.optimize import router as optimize_router
from app.api.seed_rides import router as seed_rides_router
from app.api.bidding import router as bidding_router
from app.services.bidding.blockchain_adapter import BlockchainAdapter
from app.services.bidding import lifecycle_controller

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup/shutdown events.
    Initializes blockchain adapter if environment variables are set.
    """
    # Startup
    rpc_url = os.getenv("BLOCKCHAIN_RPC_URL")
    auction_address = os.getenv("RIDE_AUCTION_ADDRESS")
    payment_address = os.getenv("PAYMENT_EXECUTOR_ADDRESS")
    admin_key = os.getenv("ADMIN_PRIVATE_KEY")
    
    if all([rpc_url, auction_address, payment_address, admin_key]):
        try:
            adapter = BlockchainAdapter(
                rpc_url=rpc_url,
                ride_auction_address=auction_address,
                payment_executor_address=payment_address,
                private_key=admin_key
            )
            lifecycle_controller.set_blockchain_adapter(adapter)
            logger.info(f"Blockchain adapter initialized: RPC={rpc_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize blockchain adapter: {e}")
    else:
        logger.warning("Blockchain environment variables not set. Bidding endpoints will return 503.")
    
    yield  # App runs here
    
    # Shutdown (cleanup if needed)
    logger.info("Application shutting down")


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
    
    **Bidding Endpoints:**
    - POST /bidding/start - Start blockchain auction
    - GET /bidding/status/{bundle_id} - Get auction status
    - POST /bidding/finalize/{bundle_id} - Finalize and get winner
    """,
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(seed_rides_router)
app.include_router(bidding_router)


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
        "health": "/health",
        "bidding": "/bidding"
    }
