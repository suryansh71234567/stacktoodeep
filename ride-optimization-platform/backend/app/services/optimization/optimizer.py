"""
Optimization Service - Main Orchestrator.

This is the high-level service that coordinates the entire optimization process:
1. Validate input rides
2. Pool compatible rides together
3. Solve routing for each pool
4. Calculate pricing and metrics
5. Return optimization results

The OptimizationService is the main entry point for the optimization pipeline.
"""
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models.ride import RideRequest, Location
from app.models.optimization import (
    OptimizationInput,
    OptimizationOutput,
    OptimizationMetrics,
    RideBundle,
    UserRideInfo
)
from app.models.route import VehicleRoute, Stop, StopType
from app.models.pricing import PricingBreakdown
from app.services.optimization.pooling import (
    RidePooler, 
    get_ride_pooler, 
    pool_rides, 
    compute_cluster_time_window,
    haversine_distance_km,
    estimate_geographic_distance
)
from app.services.optimization.solver import RouteSolver, get_route_solver, solve_cluster
from app.services.pricing_engine import PricingEngine, get_pricing_engine, compute_pricing
from app.services.optimization.utils import (
    compute_pooling_efficiency,
    compute_individual_route_distance
)
from app.services.discount_calculator import compute_flex_score, compute_user_savings
from app.utils.routing import RoutingService, get_routing_service


# Logging
logger = logging.getLogger(__name__)

# Constants
AVERAGE_SPEED_KMH = 30.0


# =============================================================================
# Helper Functions
# =============================================================================

def generate_route_string(cluster: List[RideRequest], route) -> str:
    """
    Generate abstract route representation from stops.
    Format: pickup1->pickup2->drop1->drop2
    """
    if not route or not route.stops:
        return ""
    
    route_parts = []
    for stop in route.stops:
        user_id = "unknown"
        for ride in cluster:
            if str(ride.id) == str(stop.ride_request_id):
                user_id = ride.user_id or str(ride.id)[:8]
                break
        
        if stop.stop_type == StopType.PICKUP:
            route_parts.append(f"pickup_{user_id}")
        else:
            route_parts.append(f"drop_{user_id}")
    
    return "->".join(route_parts)


def compute_user_times(cluster: List[RideRequest], route, cluster_start: datetime) -> List[UserRideInfo]:
    """
    Compute per-user pickup and drop times based on route sequence.
    """
    users_info = []
    
    current_time = cluster_start
    stop_times = {}
    
    for i, stop in enumerate(route.stops):
        if i > 0:
            prev_stop = route.stops[i - 1]
            dist = haversine_distance_km(
                prev_stop.lat, prev_stop.lng,
                stop.lat, stop.lng
            )
            travel_time_min = (dist / AVERAGE_SPEED_KMH) * 60
            current_time = current_time + timedelta(minutes=travel_time_min)
        
        key = (str(stop.ride_request_id), stop.stop_type.value)
        stop_times[key] = current_time
    
    for ride in cluster:
        ride_id_str = str(ride.id)
        
        pickup_time = stop_times.get((ride_id_str, "pickup"), cluster_start)
        drop_time = stop_times.get((ride_id_str, "drop"), cluster_start + timedelta(minutes=30))
        
        user_info = UserRideInfo(
            user_id=ride.user_id or ride_id_str[:8],
            pickup_location=ride.pickup,
            pickup_time=pickup_time,
            drop_location=ride.drop,
            drop_time=drop_time
        )
        users_info.append(user_info)
    
    return users_info


# =============================================================================
# OptimizationService Class
# =============================================================================

class OptimizationService:
    """
    High-level service that coordinates the entire optimization process.
    """
    
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        pricing_engine: Optional[PricingEngine] = None,
        pooler: Optional[RidePooler] = None,
        solver: Optional[RouteSolver] = None,
    ):
        self.routing_service = routing_service or get_routing_service()
        self.pricing_engine = pricing_engine or get_pricing_engine()
        self.pooler = pooler or get_ride_pooler()
        self.solver = solver or get_route_solver()
    
    async def optimize(
        self,
        rides: List[RideRequest]
    ) -> OptimizationOutput:
        """
        Main entry point for optimization.
        """
        start_time = time.time()
        
        logger.info(f"Starting optimization for {len(rides)} rides")
        
        if not rides:
            return self._empty_output()
        
        try:
            # Step 1: Pool compatible rides
            groups = self.pooler.find_compatible_groups(rides)
            logger.info(f"Formed {len(groups)} groups from {len(rides)} rides")
            
            # Step 2: Solve routing for each group
            routes = []
            for i, group in enumerate(groups):
                try:
                    route = await self._optimize_single_pool(group)
                    if route:
                        routes.append(route)
                except Exception as e:
                    logger.warning(f"Failed to optimize group {i}: {e}")
                    fallback_routes = self._fallback_solo_routes(group)
                    routes.extend(fallback_routes)
            
            # Step 3: Calculate pricing
            total_cost = 0.0
            total_savings = 0.0
            
            for route in routes:
                earnings = self.pricing_engine.calculate_driver_earnings(route)
                route.revenue = earnings["gross_revenue"]
                total_cost += earnings["gross_revenue"]
            
            savings_info = self.pricing_engine.estimate_savings(rides, routes)
            total_savings = savings_info["total_savings"]
            
            # Step 4: Calculate metrics
            metrics = self._calculate_metrics(routes, rides)
            
            optimization_time = time.time() - start_time
            
            status = "success" if routes else "failed"
            
            return OptimizationOutput(
                bundles=self._routes_to_bundles(routes, rides),
                total_rides_processed=len(rides),
                total_bundles_created=len(routes),
                optimization_metrics={
                    "total_cost": round(total_cost, 2),
                    "total_savings": round(total_savings, 2),
                    "optimization_time_seconds": round(optimization_time, 2),
                    "status": status,
                }
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            routes = self._fallback_solo_routes(rides)
            
            return OptimizationOutput(
                bundles=[],
                total_rides_processed=len(rides),
                total_bundles_created=len(routes),
                optimization_metrics={"status": "partial", "error": str(e)}
            )
    
    async def _optimize_single_pool(
        self,
        rides: List[RideRequest]
    ) -> Optional[VehicleRoute]:
        if not rides:
            return None
        
        if len(rides) == 1:
            return self._create_solo_route(rides[0])
        
        routes = await self.solver.solve(rides, num_vehicles=1)
        
        if routes:
            return routes[0]
        
        return solve_cluster(rides)
    
    def _calculate_metrics(
        self,
        routes: List[VehicleRoute],
        original_rides: List[RideRequest]
    ) -> OptimizationMetrics:
        if not routes or not original_rides:
            return OptimizationMetrics()
        
        total_stops = sum(len(r.stops) for r in routes)
        rides_pooled = total_stops // 2
        
        vehicles_used = len(routes)
        pooling_efficiency = rides_pooled / vehicles_used if vehicles_used > 0 else 0
        
        return OptimizationMetrics(
            rides_pooled=int(rides_pooled),
            vehicles_used=vehicles_used,
            pooling_efficiency=round(pooling_efficiency, 2),
        )
    
    def _create_solo_route(self, ride: RideRequest) -> VehicleRoute:
        dist = estimate_geographic_distance(ride.pickup, ride.dropoff)
        duration = int((dist / 30) * 60)
        
        return VehicleRoute(
            vehicle_id=f"vehicle_{uuid.uuid4().hex[:8]}",
            stops=[
                Stop(
                    ride_id=str(ride.id),
                    location=ride.pickup,
                    type="pickup",
                    time_window=ride.time_window,
                    num_passengers=ride.num_passengers,
                    sequence=0,
                ),
                Stop(
                    ride_id=str(ride.id),
                    location=ride.dropoff,
                    type="dropoff",
                    time_window=ride.time_window,
                    num_passengers=ride.num_passengers,
                    sequence=1,
                ),
            ],
            total_distance_km=round(dist, 2),
            total_duration_minutes=duration,
            capacity_used=ride.num_passengers,
            revenue=0.0,
            load_profile=[ride.num_passengers, 0],
        )
    
    def _fallback_solo_routes(self, rides: List[RideRequest]) -> List[VehicleRoute]:
        return [self._create_solo_route(ride) for ride in rides]
    
    def _empty_output(self) -> OptimizationOutput:
        return OptimizationOutput(
            bundles=[],
            total_rides_processed=0,
            total_bundles_created=0,
            optimization_metrics={}
        )
    
    def _routes_to_bundles(
        self,
        routes: List[VehicleRoute],
        rides: List[RideRequest]
    ) -> List[RideBundle]:
        bundles = []
        rides_by_id = {str(r.id): r for r in rides}
        
        for route in routes:
            ride_ids = list(set(stop.ride_id for stop in route.stops))
            cluster = [rides_by_id[rid] for rid in ride_ids if rid in rides_by_id]
            
            if not cluster:
                continue
            
            time_window = compute_cluster_time_window(cluster)
            cluster_start = time_window[0] if time_window else datetime.utcnow()
            
            cost_without = sum(
                compute_individual_route_distance(r) * 10
                for r in cluster
            )
            
            cluster_savings = 0.0
            for ride in cluster:
                flex_score = compute_flex_score(ride.buffer_before_min, ride.buffer_after_min)
                cluster_savings += compute_user_savings(flex_score)
            
            pooling_eff = compute_pooling_efficiency(len(cluster), len(rides))
            pricing = compute_pricing(route.total_distance_km, pooling_eff, cluster_savings)
            
            bundle = RideBundle(
                route=generate_route_string(cluster, route),
                users=compute_user_times(cluster, route, cluster_start),
                distance=route.total_distance_km,
                duration=getattr(route, 'total_duration_min', route.total_duration_minutes),
                cost_without_optimization=round(cost_without, 2),
                optimized_cost=round(route.total_distance_km * 10, 2),
                ride_request_ids=[str(ride.id) for ride in cluster],
                detailed_route=route,
                pricing=pricing
            )
            bundles.append(bundle)
        
        return bundles


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def optimize_rides(ride_requests: List[RideRequest]) -> OptimizationOutput:
    """
    Main orchestration function for ride optimization (legacy sync version).
    """
    if not ride_requests:
        return OptimizationOutput(
            bundles=[],
            total_rides_processed=0,
            total_bundles_created=0,
            optimization_metrics={}
        )
    
    clusters = pool_rides(ride_requests)
    
    bundles = []
    total_user_savings = 0.0
    
    for cluster in clusters:
        route = solve_cluster(cluster)
        time_window = compute_cluster_time_window(cluster)
        cluster_start = time_window[0] if time_window else datetime.utcnow()
        
        cost_without_optimization = sum(
            compute_individual_route_distance(ride) * 10
            for ride in cluster
        )
        
        cluster_savings = 0.0
        for ride in cluster:
            flex_score = compute_flex_score(
                ride.buffer_before_min,
                ride.buffer_after_min
            )
            cluster_savings += compute_user_savings(flex_score)
        
        total_user_savings += cluster_savings
        
        pooling_efficiency = compute_pooling_efficiency(
            len(cluster), 
            len(ride_requests)
        )
        
        optimized_cost = route.total_distance_km * 10
        route_string = generate_route_string(cluster, route)
        users_info = compute_user_times(cluster, route, cluster_start)
        
        pricing = compute_pricing(
            route_distance_km=route.total_distance_km,
            pooling_efficiency=pooling_efficiency,
            total_user_savings=cluster_savings
        )
        
        bundle = RideBundle(
            route=route_string,
            users=users_info,
            distance=route.total_distance_km,
            duration=getattr(route, 'total_duration_min', 0.0),
            cost_without_optimization=round(cost_without_optimization, 2),
            optimized_cost=round(optimized_cost, 2),
            ride_request_ids=[str(ride.id) for ride in cluster],
            detailed_route=route,
            pricing=pricing
        )
        bundles.append(bundle)
    
    avg_pooling = sum(
        compute_pooling_efficiency(len(c), len(ride_requests))
        for c in clusters
    ) / len(clusters) if clusters else 0.0
    
    return OptimizationOutput(
        bundles=bundles,
        total_rides_processed=len(ride_requests),
        total_bundles_created=len(bundles),
        optimization_metrics={
            "avg_pooling_efficiency": round(avg_pooling, 4),
            "total_user_savings": round(total_user_savings, 2),
            "total_clusters": len(clusters),
        }
    )


# =============================================================================
# Module-level convenience
# =============================================================================

_default_service: Optional[OptimizationService] = None


def get_optimization_service() -> OptimizationService:
    """Get or create the default optimization service."""
    global _default_service
    if _default_service is None:
        _default_service = OptimizationService()
    return _default_service
