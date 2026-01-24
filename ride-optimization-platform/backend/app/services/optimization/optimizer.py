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
from datetime import datetime
from typing import Dict, List, Optional

from app.models.ride import RideRequest
from app.models.optimization import (
    OptimizationInput,
    OptimizationOutput,
    OptimizationMetrics,
    RideBundle,
)
from app.models.route import VehicleRoute, Stop
from app.models.pricing import PricingBreakdown
from app.services.optimization.pooling import RidePooler, get_ride_pooler
from app.services.optimization.solver import RouteSolver, get_route_solver, solve_cluster
from app.services.pricing_engine import PricingEngine, get_pricing_engine, compute_pricing
from app.services.optimization.utils import compute_pooling_efficiency
from app.services.discount_calculator import compute_flex_score, compute_user_savings
from app.utils.routing import RoutingService, get_routing_service


# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# OptimizationService Class
# =============================================================================

class OptimizationService:
    """
    High-level service that coordinates the entire optimization process.
    
    This is the main entry point for ride optimization. It:
    1. Validates input rides
    2. Groups compatible rides using RidePooler
    3. Solves routing for each group using RouteSolver
    4. Calculates pricing using PricingEngine
    5. Returns structured output with metrics
    
    Example:
        >>> service = OptimizationService()
        >>> output = await service.optimize(rides)
        >>> print(f"Status: {output.status}, Savings: ${output.total_savings}")
    """
    
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        pricing_engine: Optional[PricingEngine] = None,
        pooler: Optional[RidePooler] = None,
        solver: Optional[RouteSolver] = None,
    ):
        """
        Initialize the optimization service.
        
        Args:
            routing_service: Service for road distance calculations
            pricing_engine: Engine for pricing calculations
            pooler: Service for grouping compatible rides
            solver: Solver for route optimization
        """
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
        
        Steps:
        a) Validate input (min 2 rides for pooling, valid time windows)
        b) Find compatible ride groups using RidePooler
        c) For each group, solve routing with RouteSolver
        d) Calculate pricing with PricingEngine
        e) Generate OptimizationOutput with metrics
        
        Args:
            rides: List of ride requests to optimize
            
        Returns:
            OptimizationOutput with routes, pricing, and metrics
            Status will be "success", "partial", or "failed"
            
        Example:
            >>> output = await service.optimize(rides)
            >>> if output.status == "success":
            ...     print(f"Optimized into {len(output.routes)} routes")
        """
        start_time = time.time()
        bundle_id = uuid.uuid4()
        
        logger.info(f"Starting optimization for {len(rides)} rides")
        
        # Validate input
        if not rides:
            return self._empty_output(bundle_id)
        
        # Validate all rides
        validation_errors = self._validate_input(rides)
        if validation_errors:
            logger.warning(f"Validation errors: {validation_errors}")
            # Continue with valid rides only if possible
            rides = [r for r in rides if r not in validation_errors]
            if not rides:
                return self._failed_output(bundle_id, "All rides failed validation")
        
        try:
            # Step 1: Pool compatible rides
            logger.info("Pooling compatible rides...")
            groups = self.pooler.find_compatible_groups(rides)
            logger.info(f"Formed {len(groups)} groups from {len(rides)} rides")
            
            # Step 2: Solve routing for each group
            logger.info("Solving routes for each group...")
            routes = []
            
            for i, group in enumerate(groups):
                try:
                    route = await self._optimize_single_pool(group)
                    if route:
                        routes.append(route)
                        logger.debug(f"Group {i}: {len(group)} rides -> 1 route")
                except Exception as e:
                    logger.warning(f"Failed to optimize group {i}: {e}")
                    # Fallback: each ride gets its own vehicle
                    fallback_routes = self._fallback_solo_routes(group)
                    routes.extend(fallback_routes)
            
            # Step 3: Calculate pricing for routes
            logger.info("Calculating pricing...")
            total_cost = 0.0
            total_savings = 0.0
            
            for route in routes:
                # Calculate earnings and update route
                earnings = self.pricing_engine.calculate_driver_earnings(route)
                route.revenue = earnings["gross_revenue"]
                total_cost += earnings["gross_revenue"]
            
            # Estimate savings vs solo rides
            savings_info = self.pricing_engine.estimate_savings(rides, routes)
            total_savings = savings_info["total_savings"]
            
            # Step 4: Calculate metrics
            metrics = self._calculate_metrics(routes, rides)
            
            # Step 5: Validate solution
            is_valid = self._validate_solution(routes, rides)
            
            # Calculate optimization time
            optimization_time = time.time() - start_time
            
            # Determine status
            if not routes:
                status = "failed"
            elif not is_valid:
                status = "partial"
            else:
                status = "success"
            
            logger.info(
                f"Optimization complete: status={status}, "
                f"routes={len(routes)}, time={optimization_time:.2f}s"
            )
            
            return OptimizationOutput(
                bundle_id=bundle_id,
                routes=routes,
                total_cost=total_cost,
                total_savings=total_savings,
                optimization_time_seconds=optimization_time,
                status=status,
                metrics=metrics,
                # Legacy fields for backward compatibility
                bundles=self._routes_to_bundles(routes, rides),
                total_rides_processed=len(rides),
                total_bundles_created=len(routes),
            )
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            optimization_time = time.time() - start_time
            
            # Fallback: return solo routes for all rides
            logger.info("Falling back to solo routes")
            routes = self._fallback_solo_routes(rides)
            
            return OptimizationOutput(
                bundle_id=bundle_id,
                routes=routes,
                total_cost=0.0,
                total_savings=0.0,
                optimization_time_seconds=optimization_time,
                status="partial",
                metrics=OptimizationMetrics(),
                bundles=[],
                total_rides_processed=len(rides),
                total_bundles_created=len(routes),
            )
    
    async def _optimize_single_pool(
        self,
        rides: List[RideRequest]
    ) -> Optional[VehicleRoute]:
        """
        Optimize a single group of compatible rides.
        
        Args:
            rides: List of compatible rides to route together
            
        Returns:
            VehicleRoute if successful, None otherwise
        """
        if not rides:
            return None
        
        if len(rides) == 1:
            # Single ride - create simple route
            return self._create_solo_route(rides[0])
        
        # Use solver for multiple rides
        routes = await self.solver.solve(rides, num_vehicles=1)
        
        if routes:
            return routes[0]
        
        # Fallback to legacy solver
        return solve_cluster(rides)
    
    def _calculate_metrics(
        self,
        routes: List[VehicleRoute],
        original_rides: List[RideRequest]
    ) -> OptimizationMetrics:
        """
        Calculate optimization quality metrics.
        
        Args:
            routes: Optimized vehicle routes
            original_rides: Original ride requests
            
        Returns:
            OptimizationMetrics with quality indicators
        """
        if not routes or not original_rides:
            return OptimizationMetrics()
        
        # Count rides per route
        total_stops = sum(len(r.stops) for r in routes)
        rides_pooled = total_stops // 2  # Each ride has pickup + dropoff
        
        vehicles_used = len(routes)
        
        # Calculate average detour (simplified estimate)
        total_detour = 0.0
        for route in routes:
            # Estimate detour as extra time vs direct routes
            if len(route.stops) > 2:
                base_time = route.total_duration_minutes / (len(route.stops) / 2)
                extra_time = route.total_duration_minutes - base_time * (len(route.stops) / 2)
                total_detour += max(0, extra_time)
        
        average_detour = total_detour / vehicles_used if vehicles_used > 0 else 0
        
        # Pooling efficiency
        pooling_efficiency = rides_pooled / vehicles_used if vehicles_used > 0 else 0
        
        # Distance saved (compare pooled vs solo)
        total_pooled_distance = sum(r.total_distance_km for r in routes)
        estimated_solo_distance = total_pooled_distance * 1.3  # Assume 30% more for solo
        total_distance_saved = max(0, estimated_solo_distance - total_pooled_distance)
        
        return OptimizationMetrics(
            rides_pooled=int(rides_pooled),
            vehicles_used=vehicles_used,
            average_detour_minutes=round(average_detour, 2),
            pooling_efficiency=round(pooling_efficiency, 2),
            total_distance_saved_km=round(total_distance_saved, 2),
        )
    
    def _validate_solution(
        self,
        routes: List[VehicleRoute],
        rides: List[RideRequest]
    ) -> bool:
        """
        Verify optimization constraints are satisfied.
        
        Checks:
        a) All rides assigned to exactly one vehicle
        b) No capacity violations
        c) Time windows respected (best effort)
        d) Pickup before dropoff for each ride
        
        Args:
            routes: Optimized routes
            rides: Original rides
            
        Returns:
            True if all constraints satisfied
        """
        if not routes:
            return False
        
        # Track which rides are assigned
        assigned_rides = set()
        violations = []
        
        for route in routes:
            current_load = 0
            pickups_done = set()
            
            for stop in route.stops:
                ride_id = stop.ride_id
                
                # Check pickup/dropoff order
                if stop.type == "pickup":
                    pickups_done.add(ride_id)
                    current_load += stop.num_passengers
                    
                    # Check capacity
                    if current_load > 4:
                        violations.append(f"Capacity violation at {ride_id}")
                        
                elif stop.type == "dropoff":
                    if ride_id not in pickups_done:
                        violations.append(f"Dropoff before pickup for {ride_id}")
                    current_load -= stop.num_passengers
                
                # Track assignment
                if stop.type == "pickup":
                    if ride_id in assigned_rides:
                        violations.append(f"Ride {ride_id} assigned multiple times")
                    assigned_rides.add(ride_id)
        
        # Check all rides assigned
        expected_rides = {str(r.id) for r in rides}
        unassigned = expected_rides - assigned_rides
        if unassigned:
            violations.append(f"Unassigned rides: {unassigned}")
        
        if violations:
            for v in violations:
                logger.warning(f"Constraint violation: {v}")
            return False
        
        return True
    
    def _validate_input(self, rides: List[RideRequest]) -> List[RideRequest]:
        """
        Validate input rides and return list of invalid ones.
        """
        invalid = []
        for ride in rides:
            # Check time window validity
            if ride.time_window.earliest >= ride.time_window.latest:
                invalid.append(ride)
                continue
            
            # Check location validity
            if not (-90 <= ride.pickup.latitude <= 90):
                invalid.append(ride)
                continue
            if not (-90 <= ride.dropoff.latitude <= 90):
                invalid.append(ride)
                continue
        
        return invalid
    
    def _create_solo_route(self, ride: RideRequest) -> VehicleRoute:
        """Create a single-ride route."""
        from app.services.optimization.pooling import estimate_geographic_distance
        
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
        """Create solo routes for all rides (fallback on error)."""
        return [self._create_solo_route(ride) for ride in rides]
    
    def _empty_output(self, bundle_id: uuid.UUID) -> OptimizationOutput:
        """Return empty output for no rides."""
        return OptimizationOutput(
            bundle_id=bundle_id,
            routes=[],
            total_cost=0.0,
            total_savings=0.0,
            optimization_time_seconds=0.0,
            status="success",
            metrics=OptimizationMetrics(),
        )
    
    def _failed_output(self, bundle_id: uuid.UUID, reason: str) -> OptimizationOutput:
        """Return failed output."""
        logger.error(f"Optimization failed: {reason}")
        return OptimizationOutput(
            bundle_id=bundle_id,
            routes=[],
            total_cost=0.0,
            total_savings=0.0,
            optimization_time_seconds=0.0,
            status="failed",
            metrics=OptimizationMetrics(),
        )
    
    def _routes_to_bundles(
        self,
        routes: List[VehicleRoute],
        rides: List[RideRequest]
    ) -> List[RideBundle]:
        """Convert routes to legacy RideBundle format."""
        bundles = []
        rides_by_id = {str(r.id): r for r in rides}
        
        for route in routes:
            # Find ride IDs in this route
            ride_ids = list(set(stop.ride_id for stop in route.stops))
            ride_uuids = []
            time_start = datetime.utcnow()
            time_end = datetime.utcnow()
            
            for rid in ride_ids:
                if rid in rides_by_id:
                    ride = rides_by_id[rid]
                    ride_uuids.append(ride.id)
                    if ride.time_window.earliest < time_start:
                        time_start = ride.time_window.earliest
                    if ride.time_window.latest > time_end:
                        time_end = ride.time_window.latest
            
            bundle = RideBundle(
                ride_request_ids=ride_uuids,
                route=route,
                pricing=PricingBreakdown(
                    baseline_driver_profit=route.revenue,
                    optimized_driver_profit=route.revenue,
                    total_user_savings=0.0,
                    broker_commission=route.revenue * 0.15,
                    pooling_efficiency=len(ride_ids) / 1.0,
                ),
                time_window_start=time_start,
                time_window_end=time_end,
            )
            bundles.append(bundle)
        
        return bundles


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def optimize_rides(ride_requests: List[RideRequest]) -> OptimizationOutput:
    """
    Main orchestration function for ride optimization (legacy sync version).
    
    For async usage, use OptimizationService.optimize() instead.
    """
    if not ride_requests:
        return OptimizationOutput(
            bundles=[],
            total_rides_processed=0,
            total_bundles_created=0,
            optimization_metrics={}
        )
    
    from app.services.optimization.pooling import pool_rides, compute_cluster_time_window
    
    # Pool rides into clusters
    clusters = pool_rides(ride_requests)
    
    # Process each cluster
    bundles = []
    total_user_savings = 0.0
    
    for cluster in clusters:
        route = solve_cluster(cluster)
        time_window = compute_cluster_time_window(cluster)
        
        # Compute user savings
        cluster_savings = 0.0
        for ride in cluster:
            flex_score = compute_flex_score(
                ride.buffer_before_min,
                ride.buffer_after_min
            )
            cluster_savings += compute_user_savings(flex_score)
        
        total_user_savings += cluster_savings
        
        # Compute pricing
        pooling_efficiency = compute_pooling_efficiency(len(cluster), len(ride_requests))
        pricing = compute_pricing(
            route_distance_km=route.total_distance_km,
            pooling_efficiency=pooling_efficiency,
            total_user_savings=cluster_savings
        )
        
        bundle = RideBundle(
            ride_request_ids=[ride.id for ride in cluster],
            route=route,
            pricing=pricing,
            time_window_start=time_window[0] if time_window else datetime.utcnow(),
            time_window_end=time_window[1] if time_window else datetime.utcnow()
        )
        bundles.append(bundle)
    
    # Calculate metrics
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
