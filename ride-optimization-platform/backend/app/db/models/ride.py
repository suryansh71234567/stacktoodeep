"""
Ride Database Model.

This module defines the RideDB model for storing ride requests
with all necessary fields for optimization, bidding, and tracking.
"""
import enum
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    Enum,
    Float,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSON, UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class RideStatus(enum.Enum):
    """
    Ride lifecycle status enum.
    
    Tracks the ride through the complete flow:
    REQUESTED -> OPTIMIZING -> BIDDING -> CONFIRMED -> COMPLETED
                                       |
                                       -> CANCELLED (can happen at any stage)
    """
    
    # Initial state when user submits ride request
    REQUESTED = "requested"
    
    # Being processed by optimization engine (pooling, routing)
    OPTIMIZING = "optimizing"
    
    # Optimization complete, AI agent is negotiating with drivers
    BIDDING = "bidding"
    
    # Driver assigned, ride is confirmed
    CONFIRMED = "confirmed"
    
    # Ride completed successfully
    COMPLETED = "completed"
    
    # Ride cancelled by user or system
    CANCELLED = "cancelled"


class RideDB(Base, UUIDMixin, TimestampMixin):
    """
    Database model for ride requests.
    
    Stores all information needed for:
    - Ride optimization and pooling
    - AI agent bidding
    - Blockchain settlement
    - Ride tracking and history
    
    Inherits from Base, UUIDMixin, TimestampMixin which provide:
    - id (UUID primary key)
    - created_at (timestamp)
    - updated_at (timestamp)
    """
    
    # Explicitly set table name
    __tablename__ = "rides"
    
    # =========================================================================
    # User Information
    # =========================================================================
    
    # User ID from authentication system
    # Indexed for fast user ride history queries
    user_id = Column(
        String(255),
        nullable=False,
        index=True,
        doc="User identifier from auth system"
    )
    
    # =========================================================================
    # Location Information (stored as JSON for flexibility)
    # =========================================================================
    
    # Pickup location with lat, lon, and optional address
    # Example: {"lat": 28.6139, "lon": 77.2090, "address": "Connaught Place, Delhi"}
    pickup_location = Column(
        JSON,
        nullable=False,
        doc="Pickup location: {lat, lon, address?}"
    )
    
    # Dropoff location with same structure as pickup
    dropoff_location = Column(
        JSON,
        nullable=False,
        doc="Dropoff location: {lat, lon, address?}"
    )
    
    # =========================================================================
    # Time Window (flexibility for optimization)
    # =========================================================================
    
    # Time window as JSON for flexibility in structure
    # Example: {
    #   "preferred": "2024-01-15T10:00:00Z",
    #   "earliest": "2024-01-15T09:45:00Z",
    #   "latest": "2024-01-15T10:30:00Z"
    # }
    time_window = Column(
        JSON,
        nullable=False,
        doc="Time flexibility: {preferred, earliest, latest}"
    )
    
    # =========================================================================
    # Ride Parameters
    # =========================================================================
    
    # Number of passengers (affects vehicle matching)
    num_passengers = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of passengers for this ride"
    )
    
    # Maximum detour the user accepts when pooling (minutes)
    # Higher value = more pooling opportunities = more savings
    max_detour_minutes = Column(
        Integer,
        nullable=False,
        default=15,
        doc="Max acceptable detour in minutes for pooling"
    )
    
    # =========================================================================
    # Status Tracking
    # =========================================================================
    
    # Current ride status (indexed for filtering active rides)
    status = Column(
        Enum(RideStatus, name="ride_status"),
        nullable=False,
        default=RideStatus.REQUESTED,
        index=True,
        doc="Current ride lifecycle status"
    )
    
    # =========================================================================
    # Bundle & Assignment (set after optimization)
    # =========================================================================
    
    # Bundle ID - links rides that are pooled together
    # Null until optimization assigns this ride to a bundle
    bundle_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        doc="Bundle ID if ride is pooled with others"
    )
    
    # Assigned vehicle/driver ID (set after bidding completes)
    vehicle_id = Column(
        String(255),
        nullable=True,
        doc="Assigned vehicle/driver identifier"
    )
    
    # =========================================================================
    # Pricing Information
    # =========================================================================
    
    # Original price before any discounts (calculated by pricing engine)
    original_price = Column(
        Float,
        nullable=True,
        doc="Original price before flexibility discount"
    )
    
    # Final price after flexibility discount and pooling savings
    discounted_price = Column(
        Float,
        nullable=True,
        doc="Final price after all discounts applied"
    )
    
    # Blockchain transaction hash for payment (if using on-chain settlement)
    payment_tx_hash = Column(
        String(255),
        nullable=True,
        doc="Blockchain transaction hash for payment"
    )
    
    # =========================================================================
    # Indexes for Common Queries
    # =========================================================================
    
    __table_args__ = (
        # Composite index for user's active rides
        Index('ix_rides_user_status', 'user_id', 'status'),
        
        # Index for finding unbundled rides during optimization
        Index('ix_rides_status_bundle', 'status', 'bundle_id'),
        
        # Index for time-based queries
        Index('ix_rides_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<RideDB(id={self.id}, user_id={self.user_id}, status={self.status})>"
