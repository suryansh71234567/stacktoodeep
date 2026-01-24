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

# Maximum users per car (vehicle capacity constraint)
MAX_USERS_PER_CAR = 4
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

def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate straight-line distance between two points using Haversine formula.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lng2 - lng1)
    
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def estimate_geographic_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate straight-line distance between two locations using Haversine formula.
    """
    return haversine_distance_km(loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude)


def check_time_overlap(tw1: TimeWindow, tw2: TimeWindow) -> bool:
    """
    Check if two time windows overlap.
    """
    latest_start = max(tw1.earliest, tw2.earliest)
    earliest_end = min(tw1.latest, tw2.latest)
    return latest_start < earliest_end


def calculate_time_overlap_quality(tw1: TimeWindow, tw2: TimeWindow) -> float:
    """
    Calculate how well two time windows overlap (0-1 score).
    """
    if not check_time_overlap(tw1, tw2):
        return 0.0
    
    latest_start = max(tw1.earliest, tw2.earliest)
    earliest_end = min(tw1.latest, tw2.latest)
    overlap_duration = (earliest_end - latest_start).total_seconds()
    
    tw1_duration = (tw1.latest - tw1.earliest).total_seconds()
    tw2_duration = (tw2.latest - tw2.earliest).total_seconds()
    min_duration = min(tw1_duration, tw2_duration)
    
    if min_duration <= 0:
        return 0.0
    
    return min(1.0, overlap_duration / min_duration)


# =============================================================================
# RidePooler Class
# =============================================================================

class RidePooler:
    """
    Determines which rides can be pooled together.
    """
    
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        max_detour_minutes: int = DEFAULT_MAX_DETOUR_MINUTES,
        max_pickup_distance_km: float = MAX_PICKUP_DISTANCE_KM,
        vehicle_capacity: int = VEHICLE_CAPACITY,
    ):
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
        """
        max_detour = max_detour_minutes or self.max_detour_minutes
        
        # Check 1: Passenger capacity
        total_passengers = ride1.num_passengers + ride2.num_passengers
        if total_passengers > self.vehicle_capacity:
            return False
        
        # Check 2: Time window overlap
        if not check_time_overlap(ride1.time_window, ride2.time_window):
            return False
        
        # Check 3: Pickup proximity
        pickup_distance = estimate_geographic_distance(ride1.pickup, ride2.pickup)
        if pickup_distance > self.max_pickup_distance_km:
            return False
        
        # Check 4: Estimated detour
        estimated_detour = self._estimate_detour_sync(ride1, ride2)
        if estimated_detour > max_detour:
            return False
        
        return True
    
    def _estimate_detour_sync(self, ride1: RideRequest, ride2: RideRequest) -> float:
        """
        Estimate detour without async routing (for quick compatibility checks).
        """
        solo1_dist = estimate_geographic_distance(ride1.pickup, ride1.dropoff)
        p1_to_p2 = estimate_geographic_distance(ride1.pickup, ride2.pickup)
        p2_to_d1 = estimate_geographic_distance(ride2.pickup, ride1.dropoff)
        
        pooled_dist = p1_to_p2 + p2_to_d1
        extra_dist = max(0, pooled_dist - solo1_dist)
        extra_minutes = (extra_dist / 30) * 60
        
        return extra_minutes
    
    async def calculate_detour(
        self,
        ride1: RideRequest,
        ride2: RideRequest
    ) -> float:
        """
        Calculate actual detour using routing service.
        """
        try:
            _, solo1_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride1.dropoff
            ])
            _, solo2_duration, _ = await self.routing_service.get_route([
                ride2.pickup, ride2.dropoff
            ])
            
            _, pooled1_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride2.pickup, ride1.dropoff, ride2.dropoff
            ])
            
            _, pooled2_duration, _ = await self.routing_service.get_route([
                ride1.pickup, ride2.pickup, ride2.dropoff, ride1.dropoff
            ])
            
            rider1_time_order1 = pooled1_duration * 0.6
            rider1_detour_order1 = max(0, rider1_time_order1 - solo1_duration)
            
            rider1_detour_order2 = max(0, pooled2_duration - solo1_duration)
            
            rider2_detour_order1 = max(0, pooled1_duration - solo2_duration)
            rider2_detour_order2 = max(0, pooled2_duration * 0.6 - solo2_duration)
            
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
        """
        if not rides:
            return []
        
        sorted_rides = sorted(rides, key=lambda r: r.time_window.preferred)
        
        assigned = set()
        groups = []
        
        for i, seed_ride in enumerate(sorted_rides):
            if id(seed_ride) in assigned:
                continue
            
            group = [seed_ride]
            assigned.add(id(seed_ride))
            group_passengers = seed_ride.num_passengers
            
            for j, candidate in enumerate(sorted_rides):
                if id(candidate) in assigned:
                    continue
                
                if len(group) >= max_group_size:
                    break
                
                if group_passengers + candidate.num_passengers > self.vehicle_capacity:
                    continue
                
                if self.can_pool(seed_ride, candidate):
                    group.append(candidate)
                    assigned.add(id(candidate))
                    group_passengers += candidate.num_passengers
            
            groups.append(group)
        
        logger.info(f"Pooling: {len(rides)} rides -> {len(groups)} groups")
        return groups
    
    def score_pool(self, rides: List[RideRequest]) -> float:
        """
        Score how good a pool is (higher = better).
        """
        if len(rides) < 2:
            return 0.0
        
        time_scores = []
        for i in range(len(rides)):
            for j in range(i + 1, len(rides)):
                overlap = calculate_time_overlap_quality(
                    rides[i].time_window,
                    rides[j].time_window
                )
                time_scores.append(overlap)
        avg_time_overlap = sum(time_scores) / len(time_scores) if time_scores else 0
        
        pickup_distances = []
        for i in range(len(rides)):
            for j in range(i + 1, len(rides)):
                dist = estimate_geographic_distance(rides[i].pickup, rides[j].pickup)
                pickup_distances.append(dist)
        
        avg_distance = sum(pickup_distances) / len(pickup_distances) if pickup_distances else 0
        geographic_score = max(0, 1 - (avg_distance / self.max_pickup_distance_km))
        
        total_passengers = sum(r.num_passengers for r in rides)
        utilization = min(1.0, total_passengers / self.vehicle_capacity)
        
        final_score = (
            avg_time_overlap * 0.35 +
            geographic_score * 0.35 +
            utilization * 0.30
        ) * 100
        
        return round(final_score, 2)


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def are_rides_poolable(ride1: RideRequest, ride2: RideRequest) -> bool:
    """
    Check if two rides can be pooled (legacy function).
    """
    pooler = RidePooler()
    return pooler.can_pool(ride1, ride2)


def pool_rides(ride_requests: List[RideRequest]) -> List[List[RideRequest]]:
    """
    Group ride requests into poolable clusters (legacy function).
    """
    pooler = RidePooler()
    return pooler.find_compatible_groups(ride_requests)


def compute_cluster_time_window(
    cluster: List[RideRequest]
) -> Optional[Tuple[datetime, datetime]]:
    """
    Compute the common time window for a cluster of rides (legacy function).
    """
    if not cluster:
        return None
    
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
