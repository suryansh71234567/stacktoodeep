"""
Ride Pooling Logic.

This module determines which rides can be pooled together based on:
- Geographic proximity (pickup/dropoff distances)
- Time window compatibility (overlapping pickup times)
- Vehicle capacity constraints (max 4 passengers)
- Detour constraints (max additional travel time)

The RidePooler class is the main interface for pool formation.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.models.ride import RideRequest, Location, TimeWindow
from app.utils.routing import RoutingService, get_routing_service
from app.core.config import settings


# =============================================================================
# Configuration
# =============================================================================

# Maximum pickup distance for rides to be pool-compatible (km)
MAX_PICKUP_DISTANCE_KM = 2.0

# Maximum vehicle capacity
VEHICLE_CAPACITY = 4

# Default max detour in minutes
DEFAULT_MAX_DETOUR_MINUTES = 15

# Earth radius for Haversine formula
EARTH_RADIUS_KM = 6371.0

# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def estimate_geographic_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate straight-line distance between two locations using Haversine formula.
    
    The Haversine formula calculates the great-circle distance between two
    points on a sphere given their latitudes and longitudes.
    
    Args:
        loc1: First location
        loc2: Second location
        
    Returns:
        Distance in kilometers
        
    Example:
        >>> loc1 = Location(latitude=28.6139, longitude=77.2090)
        >>> loc2 = Location(latitude=28.5355, longitude=77.3910)
        >>> dist = estimate_geographic_distance(loc1, loc2)
        >>> print(f"{dist:.2f} km")
        18.52 km
    """
    lat1_rad = math.radians(loc1.latitude)
    lat2_rad = math.radians(loc2.latitude)
    delta_lat = math.radians(loc2.latitude - loc1.latitude)
    delta_lon = math.radians(loc2.longitude - loc1.longitude)
    
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def check_time_overlap(tw1: TimeWindow, tw2: TimeWindow) -> bool:
    """
    Check if two time windows overlap.
    
    Two time windows overlap if the latest start is before the earliest end.
    
    Args:
        tw1: First time window
        tw2: Second time window
        
    Returns:
        True if windows overlap, False otherwise
        
    Example:
        >>> tw1 = TimeWindow(earliest=9:00, preferred=9:15, latest=9:30)
        >>> tw2 = TimeWindow(earliest=9:20, preferred=9:30, latest=9:45)
        >>> check_time_overlap(tw1, tw2)  # Overlap from 9:20-9:30
        True
    """
    # Overlap exists if: max(start1, start2) < min(end1, end2)
    latest_start = max(tw1.earliest, tw2.earliest)
    earliest_end = min(tw1.latest, tw2.latest)
    
    return latest_start < earliest_end


def calculate_time_overlap_quality(tw1: TimeWindow, tw2: TimeWindow) -> float:
    """
    Calculate how well two time windows overlap (0-1 score).
    
    Args:
        tw1: First time window
        tw2: Second time window
        
    Returns:
        Score from 0 (no overlap) to 1 (perfect overlap)
    """
    if not check_time_overlap(tw1, tw2):
        return 0.0
    
    # Calculate overlap duration
    latest_start = max(tw1.earliest, tw2.earliest)
    earliest_end = min(tw1.latest, tw2.latest)
    overlap_duration = (earliest_end - latest_start).total_seconds()
    
    # Calculate minimum window duration
    tw1_duration = (tw1.latest - tw1.earliest).total_seconds()
    tw2_duration = (tw2.latest - tw2.earliest).total_seconds()
    min_duration = min(tw1_duration, tw2_duration)
    
    if min_duration <= 0:
        return 0.0
    
    # Overlap quality is ratio of overlap to smaller window
    return min(1.0, overlap_duration / min_duration)


# =============================================================================
# RidePooler Class
# =============================================================================

class RidePooler:
    """
    Determines which rides can be pooled together.
    
    Uses geographic proximity, time window compatibility, vehicle capacity,
    and detour constraints to form optimal ride pools.
    
    Example:
        >>> pooler = RidePooler(max_detour_minutes=15)
        >>> groups = await pooler.find_compatible_groups(rides)
        >>> for group in groups:
        ...     print(f"Pool of {len(group)} rides")
    """
    
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        max_detour_minutes: int = DEFAULT_MAX_DETOUR_MINUTES,
        max_pickup_distance_km: float = MAX_PICKUP_DISTANCE_KM,
        vehicle_capacity: int = VEHICLE_CAPACITY,
    ):
        """
        Initialize the ride pooler.
        
        Args:
            routing_service: Service for calculating road distances/times
            max_detour_minutes: Maximum acceptable detour for pooling
            max_pickup_distance_km: Maximum distance between pickups
            vehicle_capacity: Maximum passengers per vehicle
        """
        self.routing_service = routing_service or get_routing_service()
        self.max_detour_minutes = max_detour_minutes
        self.max_pickup_distance_km = max_pickup_distance_km
        self.vehicle_capacity = vehicle_capacity
    
    def can_pool(
        self,
        ride1: RideRequest,
        ride2: RideRequest,
        max_detour_minutes: Optional[int] = None
    ) -> bool:
        """
        Check if two rides are compatible for pooling.
        
        Criteria:
        a) Time windows overlap (pickup times must align)
        b) Geographic proximity (pickups within max_pickup_distance_km)
        c) Combined passengers ≤ vehicle capacity (4)
        d) Estimated detour won't exceed max_detour_minutes
        
        Args:
            ride1: First ride request
            ride2: Second ride request
            max_detour_minutes: Override for max detour (uses instance default if None)
            
        Returns:
            True if rides can be pooled together
            
        Example:
            >>> pooler = RidePooler()
            >>> if pooler.can_pool(ride1, ride2):
            ...     print("Rides are compatible!")
        """
        max_detour = max_detour_minutes or self.max_detour_minutes
        
        # Check 1: Passenger capacity
        total_passengers = ride1.num_passengers + ride2.num_passengers
        if total_passengers > self.vehicle_capacity:
            logger.debug(f"Cannot pool: capacity exceeded ({total_passengers} > {self.vehicle_capacity})")
            return False
        
        # Check 2: Time window overlap
        if not check_time_overlap(ride1.time_window, ride2.time_window):
            logger.debug("Cannot pool: time windows don't overlap")
            return False
        
        # Check 3: Pickup proximity
        pickup_distance = estimate_geographic_distance(ride1.pickup, ride2.pickup)
        if pickup_distance > self.max_pickup_distance_km:
            logger.debug(f"Cannot pool: pickups too far ({pickup_distance:.2f} km)")
            return False
        
        # Check 4: Estimated detour (simplified - use straight-line estimate)
        # Full detour calculation requires async routing, so we estimate here
        estimated_detour = self._estimate_detour_sync(ride1, ride2)
        if estimated_detour > max_detour:
            logger.debug(f"Cannot pool: detour too long ({estimated_detour:.1f} min)")
            return False
        
        logger.debug(f"Rides compatible: distance={pickup_distance:.2f}km, detour={estimated_detour:.1f}min")
        return True
    
    def _estimate_detour_sync(self, ride1: RideRequest, ride2: RideRequest) -> float:
        """
        Estimate detour without async routing (for quick compatibility checks).
        
        Uses straight-line distances and estimated speed.
        """
        # Solo distance for ride1
        solo1_dist = estimate_geographic_distance(ride1.pickup, ride1.dropoff)
        
        # Pooled distance (simplified: pickup1 -> pickup2 -> midpoint dropoff)
        p1_to_p2 = estimate_geographic_distance(ride1.pickup, ride2.pickup)
        p2_to_d1 = estimate_geographic_distance(ride2.pickup, ride1.dropoff)
        
        pooled_dist = p1_to_p2 + p2_to_d1
        
        # Extra distance for ride1 passenger
        extra_dist = max(0, pooled_dist - solo1_dist)
        
        # Convert to time (assume 30 km/h average speed in city)
        extra_minutes = (extra_dist / 30) * 60
        
        return extra_minutes
    
    async def calculate_detour(
        self,
        ride1: RideRequest,
        ride2: RideRequest
    ) -> float:
        """
        Calculate actual detour using routing service.
        
        Compares solo routes vs pooled routes for all permutations
        and returns the maximum detour either passenger would experience.
        
        Args:
            ride1: First ride
            ride2: Second ride
            
        Returns:
            Maximum detour in minutes for either passenger
            
        Example:
            >>> detour = await pooler.calculate_detour(ride1, ride2)
            >>> print(f"Max detour: {detour:.1f} minutes")
        """
        try:
            # Calculate solo durations
            _, solo1_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride1.dropoff
            ])
            _, solo2_duration, _ = await self.routing_service.get_route([
                ride2.pickup, ride2.dropoff
            ])
            
            # Try different pooled route orderings
            # Order 1: P1 -> P2 -> D1 -> D2
            _, pooled1_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride2.pickup, ride1.dropoff, ride2.dropoff
            ])
            
            # Order 2: P1 -> P2 -> D2 -> D1
            _, pooled2_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride2.pickup, ride2.dropoff, ride1.dropoff
            ])
            
            # Calculate detours for each order
            # For order 1: rider1 exits at D1
            rider1_time_order1 = pooled1_duration * 0.6  # Rough estimate
            rider1_detour_order1 = max(0, rider1_time_order1 - solo1_duration)
            
            # For order 2: rider1 exits last
            rider1_detour_order2 = max(0, pooled2_duration - solo1_duration)
            
            # Similarly for rider2
            rider2_detour_order1 = max(0, pooled1_duration - solo2_duration)
            rider2_detour_order2 = max(0, pooled2_duration * 0.6 - solo2_duration)
            
            # Find best order (minimizes max detour)
            max_detour_order1 = max(rider1_detour_order1, rider2_detour_order1)
            max_detour_order2 = max(rider1_detour_order2, rider2_detour_order2)
            
            return min(max_detour_order1, max_detour_order2)
            
        except Exception as e:
            logger.warning(f"Routing failed, using estimate: {e}")
            return self._estimate_detour_sync(ride1, ride2)
    
    def find_compatible_groups(
        self,
        rides: List[RideRequest],
        max_group_size: int = 4
    ) -> List[List[RideRequest]]:
        """
        Group rides into compatible pools using greedy clustering.
        
        Algorithm:
        1. Sort rides by preferred pickup time
        2. For each unassigned ride, start a new group
        3. Add compatible rides to the group (up to max_group_size)
        4. Maximize pooling by checking all compatible candidates
        
        Args:
            rides: List of ride requests to pool
            max_group_size: Maximum rides per pool (default 4)
            
        Returns:
            List of ride groups (each group shares a vehicle)
            
        Example:
            >>> groups = pooler.find_compatible_groups(rides, max_group_size=3)
            >>> print(f"Formed {len(groups)} pools from {len(rides)} rides")
        """
        if not rides:
            return []
        
        # Sort by preferred pickup time
        sorted_rides = sorted(rides, key=lambda r: r.time_window.preferred)
        
        assigned = set()
        groups = []
        
        for i, seed_ride in enumerate(sorted_rides):
            if id(seed_ride) in assigned:
                continue
            
            # Start new group with seed
            group = [seed_ride]
            assigned.add(id(seed_ride))
            group_passengers = seed_ride.num_passengers
            
            # Find compatible rides for this group
            for j, candidate in enumerate(sorted_rides):
                if id(candidate) in assigned:
                    continue
                
                # Check group size limit
                if len(group) >= max_group_size:
                    break
                
                # Check capacity
                if group_passengers + candidate.num_passengers > self.vehicle_capacity:
                    continue
                
                # Check compatibility with seed (simplified - check with seed only)
                if self.can_pool(seed_ride, candidate):
                    group.append(candidate)
                    assigned.add(id(candidate))
                    group_passengers += candidate.num_passengers
            
            groups.append(group)
            logger.debug(f"Formed group with {len(group)} rides, {group_passengers} passengers")
        
        logger.info(f"Pooling: {len(rides)} rides -> {len(groups)} groups")
        return groups
    
    def score_pool(self, rides: List[RideRequest]) -> float:
        """
        Score how good a pool is (higher = better).
        
        Scoring factors:
        - Time overlap quality (0-1): How well pickup times align
        - Geographic compactness (0-1): How close pickups/dropoffs are
        - Passenger utilization (0-1): total_passengers / vehicle_capacity
        
        Final score is weighted average × 100.
        
        Args:
            rides: List of rides in the pool
            
        Returns:
            Score from 0 to 100 (higher = better pool)
            
        Example:
            >>> score = pooler.score_pool([ride1, ride2, ride3])
            >>> print(f"Pool quality: {score:.1f}/100")
        """
        if len(rides) < 2:
            return 0.0  # No pooling happening
        
        # Factor 1: Time overlap quality (average pairwise overlap)
        time_scores = []
        for i in range(len(rides)):
            for j in range(i + 1, len(rides)):
                overlap = calculate_time_overlap_quality(
                    rides[i].time_window,
                    rides[j].time_window
                )
                time_scores.append(overlap)
        avg_time_overlap = sum(time_scores) / len(time_scores) if time_scores else 0
        
        # Factor 2: Geographic compactness (based on pickup distances)
        pickup_distances = []
        for i in range(len(rides)):
            for j in range(i + 1, len(rides)):
                dist = estimate_geographic_distance(rides[i].pickup, rides[j].pickup)
                pickup_distances.append(dist)
        
        # Normalize: 0km = 1.0, max_pickup_distance_km = 0.0
        avg_distance = sum(pickup_distances) / len(pickup_distances) if pickup_distances else 0
        geographic_score = max(0, 1 - (avg_distance / self.max_pickup_distance_km))
        
        # Factor 3: Passenger utilization
        total_passengers = sum(r.num_passengers for r in rides)
        utilization = min(1.0, total_passengers / self.vehicle_capacity)
        
        # Weighted average (time and geography more important)
        final_score = (
            avg_time_overlap * 0.35 +
            geographic_score * 0.35 +
            utilization * 0.30
        ) * 100
        
        logger.debug(
            f"Pool score: {final_score:.1f} "
            f"(time={avg_time_overlap:.2f}, geo={geographic_score:.2f}, util={utilization:.2f})"
        )
        
        return round(final_score, 2)


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def are_rides_poolable(ride1: RideRequest, ride2: RideRequest) -> bool:
    """
    Check if two rides can be pooled (legacy function).
    
    Uses RidePooler with default settings.
    """
    pooler = RidePooler()
    return pooler.can_pool(ride1, ride2)


def pool_rides(ride_requests: List[RideRequest]) -> List[List[RideRequest]]:
    """
    Group ride requests into poolable clusters (legacy function).
    
    Uses RidePooler with default settings.
    """
    pooler = RidePooler()
    return pooler.find_compatible_groups(ride_requests)


def compute_cluster_time_window(
    cluster: List[RideRequest]
) -> Optional[Tuple[datetime, datetime]]:
    """
    Compute the common time window for a cluster of rides (legacy function).
    
    Finds the intersection of all individual time windows.
    """
    if not cluster:
        return None
    
    # Find intersection (latest start, earliest end)
    cluster_start = max(r.time_window.earliest for r in cluster)
    cluster_end = min(r.time_window.latest for r in cluster)
    
    if cluster_start >= cluster_end:
        return None
    
    return (cluster_start, cluster_end)


# =============================================================================
# Module-level convenience
# =============================================================================

_default_pooler: Optional[RidePooler] = None


def get_ride_pooler() -> RidePooler:
    """Get or create the default ride pooler."""
    global _default_pooler
    if _default_pooler is None:
        _default_pooler = RidePooler()
    return _default_pooler
