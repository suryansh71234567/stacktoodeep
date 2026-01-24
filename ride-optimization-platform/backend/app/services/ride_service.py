"""
Ride Service - Business Logic Layer.

This service handles all ride-related business logic including:
- Creating new ride requests
- Querying rides by ID or filters
- Updating ride status
- Assigning optimization results

The service sits between the API layer and the database,
handling validation, geocoding, and data transformation.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ride import RideDB, RideStatus as DBRideStatus
from app.models.ride import (
    RideRequest,
    RideRequestCreate,
    RideStatus,
    Location,
    TimeWindow,
)
from app.utils.geocoding import geocode


# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class RideNotFoundError(Exception):
    """Ride with given ID was not found."""
    pass


class RideServiceError(Exception):
    """General ride service error."""
    pass


# =============================================================================
# RideService Class
# =============================================================================

class RideService:
    """
    Service class for ride-related business logic.
    
    Handles CRUD operations for rides, including geocoding addresses,
    managing ride lifecycle, and assigning optimization results.
    
    Example:
        >>> async with get_db() as db:
        ...     service = RideService(db)
        ...     ride = await service.create_ride(ride_data)
        ...     print(f"Created ride: {ride.id}")
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize the ride service.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
    
    # =========================================================================
    # Create Operations
    # =========================================================================
    
    async def create_ride(self, ride_data: RideRequestCreate) -> RideRequest:
        """
        Create a new ride request from simplified API input.
        
        This method:
        1. Geocodes pickup and dropoff addresses to coordinates
        2. Converts time_buffer_minutes to a TimeWindow
        3. Generates a UUID for the ride
        4. Saves to database
        5. Returns the full RideRequest model
        
        Args:
            ride_data: Simplified ride request from API
            
        Returns:
            Complete RideRequest with geocoded locations and ID
            
        Raises:
            ValueError: If addresses cannot be geocoded
            RideServiceError: If database operation fails
            
        Example:
            >>> data = RideRequestCreate(
            ...     pickup_address="Connaught Place, Delhi",
            ...     dropoff_address="Noida Sector 18",
            ...     preferred_time=datetime.now() + timedelta(hours=1),
            ...     time_buffer_minutes=30
            ... )
            >>> ride = await service.create_ride(data)
        """
        logger.info(f"Creating ride: {ride_data.pickup_address} -> {ride_data.dropoff_address}")
        
        try:
            # Step 1: Geocode addresses
            pickup_location = await geocode(ride_data.pickup_address)
            dropoff_location = await geocode(ride_data.dropoff_address)
            
            # Step 2: Create time window from buffer
            buffer = timedelta(minutes=ride_data.time_buffer_minutes)
            time_window = TimeWindow(
                earliest=ride_data.preferred_time - buffer,
                preferred=ride_data.preferred_time,
                latest=ride_data.preferred_time + buffer,
            )
            
            # Step 3: Generate ride ID
            ride_id = uuid.uuid4()
            
            # Step 4: Create database model
            db_ride = RideDB(
                id=ride_id,
                user_id="anonymous",  # Would come from auth in real app
                pickup_location={
                    "lat": pickup_location.latitude,
                    "lon": pickup_location.longitude,
                    "address": pickup_location.address,
                },
                dropoff_location={
                    "lat": dropoff_location.latitude,
                    "lon": dropoff_location.longitude,
                    "address": dropoff_location.address,
                },
                time_window={
                    "earliest": time_window.earliest.isoformat(),
                    "preferred": time_window.preferred.isoformat(),
                    "latest": time_window.latest.isoformat(),
                },
                num_passengers=ride_data.num_passengers,
                max_detour_minutes=ride_data.max_detour_minutes,
                status=DBRideStatus.REQUESTED,
            )
            
            # Step 5: Save to database
            self.db.add(db_ride)
            await self.db.commit()
            await self.db.refresh(db_ride)
            
            logger.info(f"Created ride: {ride_id}")
            
            # Step 6: Convert to Pydantic model and return
            return self._db_to_pydantic(db_ride, pickup_location, dropoff_location, time_window)
            
        except ValueError as e:
            logger.error(f"Geocoding failed: {e}")
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to create ride: {e}")
            await self.db.rollback()
            raise RideServiceError(f"Failed to create ride: {e}")
    
    # =========================================================================
    # Read Operations
    # =========================================================================
    
    async def get_ride(self, ride_id: str) -> Optional[RideRequest]:
        """
        Get a single ride by ID.
        
        Args:
            ride_id: UUID of the ride (as string)
            
        Returns:
            RideRequest if found, None otherwise
            
        Example:
            >>> ride = await service.get_ride("550e8400-e29b-41d4-a716-446655440000")
            >>> if ride:
            ...     print(f"Status: {ride.status}")
        """
        try:
            ride_uuid = uuid.UUID(ride_id)
        except ValueError:
            logger.warning(f"Invalid ride ID format: {ride_id}")
            return None
        
        result = await self.db.execute(
            select(RideDB).where(RideDB.id == ride_uuid)
        )
        db_ride = result.scalar_one_or_none()
        
        if db_ride is None:
            return None
        
        return self._db_to_pydantic_from_json(db_ride)
    
    async def list_rides(
        self,
        user_id: Optional[str] = None,
        status: Optional[RideStatus] = None,
        limit: int = 100
    ) -> List[RideRequest]:
        """
        List rides with optional filters.
        
        Args:
            user_id: Filter by user ID (optional)
            status: Filter by ride status (optional)
            limit: Maximum number of results (default 100)
            
        Returns:
            List of RideRequest objects, ordered by created_at DESC
            
        Example:
            >>> # Get all requested rides
            >>> rides = await service.list_rides(status=RideStatus.REQUESTED)
            >>> 
            >>> # Get user's rides
            >>> user_rides = await service.list_rides(user_id="user_123", limit=10)
        """
        query = select(RideDB)
        
        # Apply filters
        if user_id is not None:
            query = query.where(RideDB.user_id == user_id)
        
        if status is not None:
            # Convert Pydantic enum to DB enum
            db_status = DBRideStatus(status.value)
            query = query.where(RideDB.status == db_status)
        
        # Order by most recent first
        query = query.order_by(desc(RideDB.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        db_rides = result.scalars().all()
        
        return [self._db_to_pydantic_from_json(r) for r in db_rides]
    
    # =========================================================================
    # Update Operations
    # =========================================================================
    
    async def update_ride_status(
        self,
        ride_id: str,
        status: RideStatus
    ) -> RideRequest:
        """
        Update the status of a ride.
        
        Args:
            ride_id: UUID of the ride (as string)
            status: New status to set
            
        Returns:
            Updated RideRequest
            
        Raises:
            RideNotFoundError: If ride doesn't exist
            
        Example:
            >>> ride = await service.update_ride_status(
            ...     ride_id="550e8400-...",
            ...     status=RideStatus.OPTIMIZING
            ... )
        """
        try:
            ride_uuid = uuid.UUID(ride_id)
        except ValueError:
            raise RideNotFoundError(f"Invalid ride ID: {ride_id}")
        
        result = await self.db.execute(
            select(RideDB).where(RideDB.id == ride_uuid)
        )
        db_ride = result.scalar_one_or_none()
        
        if db_ride is None:
            raise RideNotFoundError(f"Ride not found: {ride_id}")
        
        # Update status
        db_ride.status = DBRideStatus(status.value)
        
        await self.db.commit()
        await self.db.refresh(db_ride)
        
        logger.info(f"Updated ride {ride_id} status to {status.value}")
        
        return self._db_to_pydantic_from_json(db_ride)
    
    async def assign_optimization_result(
        self,
        ride_id: str,
        bundle_id: str,
        vehicle_id: str,
        pricing: dict
    ) -> RideRequest:
        """
        Assign optimization results to a ride.
        
        Called after the optimization engine completes. Updates the ride
        with bundle assignment, vehicle assignment, and pricing.
        
        Args:
            ride_id: UUID of the ride
            bundle_id: Bundle ID from optimization
            vehicle_id: Assigned vehicle/driver ID
            pricing: Dict with 'original_price' and 'discounted_price' keys
            
        Returns:
            Updated RideRequest with status CONFIRMED
            
        Raises:
            RideNotFoundError: If ride doesn't exist
            
        Example:
            >>> ride = await service.assign_optimization_result(
            ...     ride_id="550e8400-...",
            ...     bundle_id="660e8400-...",
            ...     vehicle_id="driver_456",
            ...     pricing={"original_price": 450.0, "discounted_price": 320.0}
            ... )
        """
        try:
            ride_uuid = uuid.UUID(ride_id)
            bundle_uuid = uuid.UUID(bundle_id)
        except ValueError as e:
            raise RideNotFoundError(f"Invalid ID format: {e}")
        
        result = await self.db.execute(
            select(RideDB).where(RideDB.id == ride_uuid)
        )
        db_ride = result.scalar_one_or_none()
        
        if db_ride is None:
            raise RideNotFoundError(f"Ride not found: {ride_id}")
        
        # Update with optimization results
        db_ride.bundle_id = bundle_uuid
        db_ride.vehicle_id = vehicle_id
        db_ride.original_price = pricing.get("original_price")
        db_ride.discounted_price = pricing.get("discounted_price")
        db_ride.status = DBRideStatus.CONFIRMED
        
        await self.db.commit()
        await self.db.refresh(db_ride)
        
        logger.info(
            f"Assigned optimization to ride {ride_id}: "
            f"bundle={bundle_id}, vehicle={vehicle_id}"
        )
        
        return self._db_to_pydantic_from_json(db_ride)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _db_to_pydantic(
        self,
        db_ride: RideDB,
        pickup: Location,
        dropoff: Location,
        time_window: TimeWindow
    ) -> RideRequest:
        """Convert database model to Pydantic model with pre-built objects."""
        return RideRequest(
            id=db_ride.id,
            user_id=db_ride.user_id,
            pickup=pickup,
            dropoff=dropoff,
            time_window=time_window,
            num_passengers=db_ride.num_passengers,
            max_detour_minutes=db_ride.max_detour_minutes,
            created_at=db_ride.created_at,
            status=RideStatus(db_ride.status.value),
        )
    
    def _db_to_pydantic_from_json(self, db_ride: RideDB) -> RideRequest:
        """Convert database model to Pydantic model, parsing JSON fields."""
        # Parse pickup location
        pickup_data = db_ride.pickup_location
        pickup = Location(
            latitude=pickup_data.get("lat"),
            longitude=pickup_data.get("lon"),
            address=pickup_data.get("address"),
        )
        
        # Parse dropoff location
        dropoff_data = db_ride.dropoff_location
        dropoff = Location(
            latitude=dropoff_data.get("lat"),
            longitude=dropoff_data.get("lon"),
            address=dropoff_data.get("address"),
        )
        
        # Parse time window
        tw_data = db_ride.time_window
        time_window = TimeWindow(
            earliest=datetime.fromisoformat(tw_data.get("earliest")),
            preferred=datetime.fromisoformat(tw_data.get("preferred")),
            latest=datetime.fromisoformat(tw_data.get("latest")),
        )
        
        return RideRequest(
            id=db_ride.id,
            user_id=db_ride.user_id,
            pickup=pickup,
            dropoff=dropoff,
            time_window=time_window,
            num_passengers=db_ride.num_passengers,
            max_detour_minutes=db_ride.max_detour_minutes,
            max_price=db_ride.original_price,
            created_at=db_ride.created_at,
            status=RideStatus(db_ride.status.value),
        )


# =============================================================================
# Factory Function
# =============================================================================

def get_ride_service(db: AsyncSession) -> RideService:
    """
    Factory function to create a RideService instance.
    
    Args:
        db: SQLAlchemy async session
        
    Returns:
        Configured RideService instance
    """
    return RideService(db)
