"""
FastAPI application for the Ride Optimization Platform.
"""
import os
import sys
import logging
import time
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
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
    
    Note: Dummy users are now generated dynamically per request in optimize.py
    based on the user's source/destination coordinates.
    """
    # Startup - Blockchain
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
    
    logger.info("✅ Backend started. Dummy users are generated dynamically per request.")
    
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

# Configure logging - use standard logger for internal logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Add request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all incoming requests and outgoing responses.
    Writes directly to stderr to ensure visibility in all environments.
    """
    # Start timing
    start_time = time.time()
    
    # Get request details
    method = request.method
    path = request.url.path
    query_params = str(request.query_params) if request.query_params else "none"
    client_host = request.client.host if request.client else "unknown"
    
    # Log incoming request directly to stderr (bypasses valid buffering)
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🔵 INCOMING REQUEST", file=sys.stderr)
    print(f"   Method: {method}", file=sys.stderr)
    print(f"   Path: {path}", file=sys.stderr)
    print(f"   Query Params: {query_params}", file=sys.stderr)
    print(f"   Client: {client_host}", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    process_time_ms = round(process_time * 1000, 2)
    
    # Color code based on status
    status_code = response.status_code
    if 200 <= status_code < 300:
        status_label = "SUCCESS"
        status_icon = "✅"
    elif 400 <= status_code < 500:
        status_label = "CLIENT ERROR"
        status_icon = "⚠️"
    elif 500 <= status_code:
        status_label = "SERVER ERROR"
        status_icon = "❌"
    else:
        status_label = "INFO"
        status_icon = "ℹ️"
    
    # Log response directly to stderr
    print(f"\n{status_icon} RESPONSE - {status_label}", file=sys.stderr)
    print(f"   Status Code: {status_code}", file=sys.stderr)
    print(f"   Processing Time: {process_time_ms}ms", file=sys.stderr)
    print(f"   Path: {method} {path}", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # Add custom header with processing time
    response.headers["X-Process-Time"] = str(process_time_ms)
    
    return response

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
