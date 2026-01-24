"""
Route Solver using Google OR-Tools.

This module solves the Vehicle Routing Problem with Time Windows (VRPTW)
to optimize ride pooling routes.

OR-Tools is a powerful optimization library that finds near-optimal solutions
for complex routing problems. We use it to:
- Minimize total travel time
- Respect time window constraints
- Enforce vehicle capacity limits
- Ensure pickup happens before dropoff for each ride
"""
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from app.models.ride import RideRequest, Location, TimeWindow
from app.models.route import VehicleRoute, Stop
from app.utils.routing import RoutingService, get_routing_service
from app.core.config import settings
from app.services.optimization.pooling import estimate_geographic_distance


# Try to import OR-Tools (optional dependency)
try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False
    logging.warning("OR-Tools not installed. Using fallback greedy solver.")


# =============================================================================
# Configuration
# =============================================================================

# Maximum passengers per vehicle
VEHICLE_CAPACITY = 4

# Optimization time limit in seconds
OPTIMIZATION_TIMEOUT = getattr(settings, 'OPTIMIZATION_TIMEOUT_SECONDS', 30)

# Large value for "no route" in distance matrix
NO_ROUTE_VALUE = 999999

# Reference time for converting datetime to minutes
REFERENCE_TIME = datetime(2020, 1, 1)

# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# RouteSolver Class
# =============================================================================

class RouteSolver:
    """
    Solves the Vehicle Routing Problem with Time Windows (VRPTW).
    
    Uses Google OR-Tools to find optimal routes that:
    - Minimize total travel time
    - Respect pickup time windows
    - Enforce vehicle capacity (max 4 passengers)
    - Ensure pickup before dropoff for each ride
    
    Example:
        >>> solver = RouteSolver()
        >>> routes = await solver.solve(rides, num_vehicles=5)
        >>> for route in routes:
        ...     print(f"Vehicle serves {len(route.stops)} stops")
    """
    
    def __init__(
        self,
        routing_service: Optional[RoutingService] = None,
        time_limit_seconds: int = OPTIMIZATION_TIMEOUT,
        vehicle_capacity: int = VEHICLE_CAPACITY,
    ):
        """
        Initialize the route solver.
        
        Args:
            routing_service: Service for calculating road distances/times
            time_limit_seconds: Max optimization time
            vehicle_capacity: Max passengers per vehicle
        """
        self.routing_service = routing_service or get_routing_service()
        self.time_limit_seconds = time_limit_seconds
        self.vehicle_capacity = vehicle_capacity
    
    async def solve(
        self,
        rides: List[RideRequest],
        num_vehicles: int = 5
    ) -> List[VehicleRoute]:
        """
        Main optimization method - solve VRPTW for given rides.
        
        Uses OR-Tools RoutingIndexManager and RoutingModel to find
        optimal vehicle routes that minimize travel time while respecting
        all constraints.
        
        Args:
            rides: List of ride requests to route
            num_vehicles: Number of available vehicles
            
        Returns:
            List of VehicleRoute objects (one per vehicle with stops)
            
        Example:
            >>> routes = await solver.solve(rides, num_vehicles=3)
            >>> print(f"Using {len(routes)} vehicles")
        """
        if not rides:
            return []
        
        if not HAS_ORTOOLS:
            logger.warning("OR-Tools not available, using fallback solver")
            return self._solve_greedy(rides)
        
        logger.info(f"Solving VRPTW for {len(rides)} rides with {num_vehicles} vehicles")
        
        try:
            # Build the data model
            # Each ride has 2 stops: pickup (even index) and dropoff (odd index)
            # Plus a depot at index 0
            num_stops = len(rides) * 2 + 1  # +1 for depot
            
            # Determine reference time (earliest time in batch)
            min_time = min(r.time_window.earliest for r in rides)
            # Round down to hour for clean logs
            reference_dt = min_time.replace(minute=0, second=0, microsecond=0)
            
            # Build distance matrix (in minutes)
            distance_matrix = await self._build_distance_matrix(rides)
            
            # Build time windows
            time_windows = self._build_time_windows(rides, reference_dt)
            
            # Build demands (passengers at each stop)
            demands = self._build_demands(rides)
            
            # Create the routing index manager
            # Nodes: 0 = depot, 1,2 = ride1 (pickup, dropoff), 3,4 = ride2, etc.
            manager = pywrapcp.RoutingIndexManager(
                num_stops,      # Number of nodes
                num_vehicles,   # Number of vehicles
                0               # Depot index
            )
            
            # Create the routing model
            routing = pywrapcp.RoutingModel(manager)
            
            # Create and register transit callback
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return distance_matrix[from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            
            # Set arc cost evaluator (minimize travel time)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Add time dimension for time windows
            routing.AddDimension(
                transit_callback_index,
                60,  # Allow waiting time (60 min max)
                24 * 60,  # Max time per vehicle (24 hours in minutes)
                False,  # Don't force start cumul to zero
                'Time'
            )
            time_dimension = routing.GetDimensionOrDie('Time')
            
            # Add time window constraints
            for i, window in enumerate(time_windows):
                index = manager.NodeToIndex(i)
                time_dimension.CumulVar(index).SetRange(int(window[0]), int(window[1]))
            
            # Add capacity dimension
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return demands[from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # No slack
                [self.vehicle_capacity] * num_vehicles,  # Capacity per vehicle
                True,  # Start cumul at zero
                'Capacity'
            )
            
            # Add pickup and delivery constraints
            for ride_idx in range(len(rides)):
                pickup_index = manager.NodeToIndex(1 + ride_idx * 2)
                delivery_index = manager.NodeToIndex(2 + ride_idx * 2)
                
                # Pickup and delivery must be on same route
                routing.AddPickupAndDelivery(pickup_index, delivery_index)
                
                # Pickup must happen before delivery
                routing.solver().Add(
                    time_dimension.CumulVar(pickup_index) <=
                    time_dimension.CumulVar(delivery_index)
                )
                
                # Same vehicle for pickup and delivery
                routing.solver().Add(
                    routing.VehicleVar(pickup_index) ==
                    routing.VehicleVar(delivery_index)
                )
            
            # Set search parameters
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = self.time_limit_seconds
            
            logger.info("Starting OR-Tools optimization...")
            
            # Solve the problem
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                logger.info(f"Solution found! Objective: {solution.ObjectiveValue()}")
                return self._extract_routes(manager, routing, solution, rides)
            else:
                logger.warning("No solution found by OR-Tools, using fallback")
                return self._solve_greedy(rides)
                
        except Exception as e:
            logger.error(f"OR-Tools solver failed: {e}", exc_info=True)
            return self._solve_greedy(rides)
    
    async def _build_distance_matrix(
        self,
        rides: List[RideRequest]
    ) -> List[List[int]]:
        """
        Create distance matrix for all stops (in minutes).
        
        Matrix layout:
        - Index 0: Depot (use first pickup as depot)
        - Index 1, 2: Ride 0 (pickup, dropoff)
        - Index 3, 4: Ride 1 (pickup, dropoff)
        - etc.
        
        Args:
            rides: List of ride requests
            
        Returns:
            2D array where matrix[i][j] = travel time in minutes (as int)
        """
        num_stops = len(rides) * 2 + 1
        
        # Build list of all locations
        locations = [rides[0].pickup]  # Depot = first pickup
        for ride in rides:
            locations.append(ride.pickup)
            locations.append(ride.dropoff)
        
        # Initialize matrix with large values (no route)
        matrix = [[NO_ROUTE_VALUE] * num_stops for _ in range(num_stops)]
        
        # Fill diagonal with zeros
        for i in range(num_stops):
            matrix[i][i] = 0
        
        # Calculate travel times between all pairs
        # Use simple estimation for speed (async routing would be too slow)
        for i in range(num_stops):
            for j in range(num_stops):
                if i != j:
                    dist = estimate_geographic_distance(locations[i], locations[j])
                    # Estimate time: 30 km/h average speed
                    time_minutes = int((dist / 30) * 60)
                    matrix[i][j] = max(1, time_minutes)  # Minimum 1 minute
        
        logger.debug(f"Built {num_stops}x{num_stops} distance matrix")
        return matrix
    
    def _build_time_windows(
        self,
        rides: List[RideRequest],
        reference_dt: datetime
    ) -> List[Tuple[int, int]]:
        """
        Extract time windows for each stop.
        
        Converts datetime to minutes since reference time.
        
        Args:
            rides: List of ride requests
            reference_dt: Reference time for normalization
            
        Returns:
            List of (earliest_minutes, latest_minutes) tuples
        """
        windows = []
        
        # Depot has wide window (any time)
        windows.append((0, 24 * 60))
        
        # Each ride has pickup and dropoff windows
        for ride in rides:
            # Pickup time window
            earliest = self._datetime_to_minutes(ride.time_window.earliest, reference_dt)
            latest = self._datetime_to_minutes(ride.time_window.latest, reference_dt)
            windows.append((earliest, latest))
            
            # Dropoff window (allow 2 hours after pickup window ends)
            dropoff_earliest = earliest
            dropoff_latest = latest + 120  # 2 hours after latest pickup
            windows.append((dropoff_earliest, dropoff_latest))
        
        return windows
    
    def _build_demands(self, rides: List[RideRequest]) -> List[int]:
        """
        Build demand array for capacity constraints.
        
        Pickup adds passengers (+), dropoff removes them (-).
        
        Args:
            rides: List of ride requests
            
        Returns:
            List of demands for each node
        """
        demands = [0]  # Depot has no demand
        
        for ride in rides:
            demands.append(ride.num_passengers)   # Pickup: add passengers
            demands.append(-ride.num_passengers)  # Dropoff: remove passengers
        
        return demands
    
    def _extract_routes(
        self,
        manager,
        routing,
        solution,
        rides: List[RideRequest]
    ) -> List[VehicleRoute]:
        """
        Parse OR-Tools solution into VehicleRoute objects.
        
        Args:
            manager: RoutingIndexManager
            routing: RoutingModel
            solution: OR-Tools solution
            rides: Original ride requests
            
        Returns:
            List of VehicleRoute objects (filtered to non-empty)
        """
        routes = []
        time_dimension = routing.GetDimensionOrDie('Time')
        capacity_dimension = routing.GetDimensionOrDie('Capacity')
        
        for vehicle_id in range(routing.vehicles()):
            index = routing.Start(vehicle_id)
            stops = []
            load_profile = []
            sequence = 0
            total_time = 0
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                
                if node > 0:  # Skip depot
                    # Determine which ride and stop type
                    ride_idx = (node - 1) // 2
                    is_pickup = (node - 1) % 2 == 0
                    
                    if ride_idx < len(rides):
                        ride = rides[ride_idx]
                        location = ride.pickup if is_pickup else ride.dropoff
                        
                        stop = Stop(
                            ride_id=str(ride.id),
                            location=location,
                            type="pickup" if is_pickup else "dropoff",
                            time_window=ride.time_window,
                            num_passengers=ride.num_passengers,
                            sequence=sequence,
                        )
                        stops.append(stop)
                        
                        # Track load
                        capacity_var = capacity_dimension.CumulVar(index)
                        load_profile.append(solution.Value(capacity_var))
                        
                        sequence += 1
                
                # Get time
                time_var = time_dimension.CumulVar(index)
                total_time = solution.Value(time_var)
                
                index = solution.Value(routing.NextVar(index))
            
            # Only add routes with stops
            if stops:
                # Estimate distance from time (30 km/h)
                distance_km = (total_time / 60) * 30
                
                route = VehicleRoute(
                    vehicle_id=f"vehicle_{vehicle_id}",
                    stops=stops,
                    total_distance_km=round(distance_km, 2),
                    total_duration_minutes=total_time,
                    capacity_used=max(load_profile) if load_profile else 0,
                    revenue=0.0,  # Calculated later by pricing engine
                    load_profile=load_profile,
                )
                routes.append(route)
                logger.debug(f"Vehicle {vehicle_id}: {len(stops)} stops, {total_time} min")
        
        logger.info(f"Extracted {len(routes)} non-empty routes")
        return routes
    
    def _datetime_to_minutes(self, dt: datetime, reference_dt: datetime) -> int:
        """Convert datetime to minutes since reference time."""
        delta = dt - reference_dt
        return int(delta.total_seconds() / 60)
    
    def _solve_greedy(self, rides: List[RideRequest]) -> List[VehicleRoute]:

        """
        Fallback greedy solver when OR-Tools is not available.
        
        Simple approach: one vehicle per ride.
        """
        logger.info("Using greedy fallback solver")
        routes = []
        
        for i, ride in enumerate(rides):
            stops = [
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
            ]
            
            # Estimate distance/time
            dist = estimate_geographic_distance(ride.pickup, ride.dropoff)
            duration = int((dist / 30) * 60)
            
            route = VehicleRoute(
                vehicle_id=f"vehicle_{i}",
                stops=stops,
                total_distance_km=round(dist, 2),
                total_duration_minutes=duration,
                capacity_used=ride.num_passengers,
                revenue=0.0,
                load_profile=[ride.num_passengers, 0],
            )
            routes.append(route)
        
        return routes


# =============================================================================
# Legacy Functions (Backward Compatibility)
# =============================================================================

def solve_cluster(cluster: List[RideRequest]) -> VehicleRoute:
    """
    Solve routing for a cluster of pooled rides (legacy function).
    
    Uses simple greedy approach for backward compatibility.
    """
    if not cluster:
        return VehicleRoute(
            vehicle_id="vehicle_0",
            stops=[],
            total_distance_km=0.0,
            total_duration_minutes=0,
            capacity_used=0,
            revenue=0.0,
            load_profile=[],
        )
    
    # All pickups first, then all dropoffs
    stops = []
    sequence = 0
    passengers = 0
    load_profile = []
    
    # Add pickups
    for ride in cluster:
        stops.append(Stop(
            ride_id=str(ride.id),
            location=ride.pickup,
            type="pickup",
            time_window=ride.time_window,
            num_passengers=ride.num_passengers,
            sequence=sequence,
        ))
        passengers += ride.num_passengers
        load_profile.append(passengers)
        sequence += 1
    
    # Add dropoffs
    for ride in cluster:
        stops.append(Stop(
            ride_id=str(ride.id),
            location=ride.dropoff,
            type="dropoff",
            time_window=ride.time_window,
            num_passengers=ride.num_passengers,
            sequence=sequence,
        ))
        passengers -= ride.num_passengers
        load_profile.append(passengers)
        sequence += 1
    
    # Estimate total distance
    total_distance = 0.0
    for i in range(len(stops) - 1):
        total_distance += estimate_geographic_distance(
            stops[i].location,
            stops[i + 1].location
        )
    
    total_duration = int((total_distance / 30) * 60)
    
    return VehicleRoute(
        vehicle_id="vehicle_0",
        stops=stops,
        total_distance_km=round(total_distance, 2),
        total_duration_minutes=total_duration,
        capacity_used=max(load_profile) if load_profile else 0,
        revenue=0.0,
        load_profile=load_profile,
    )


def order_by_distance(
    rides: List[RideRequest],
    location_getter,
    start_point: tuple
) -> List[RideRequest]:
    """
    Order rides by distance from starting point (legacy function).
    """
    if len(rides) <= 1:
        return list(rides)
    
    remaining = list(rides)
    ordered = []
    current_point = start_point
    
    while remaining:
        nearest_idx = 0
        nearest_dist = float('inf')
        
        for i, ride in enumerate(remaining):
            loc = location_getter(ride)
            # Simple distance calculation
            dist = ((current_point[0] - loc[0])**2 + (current_point[1] - loc[1])**2)**0.5
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i
        
        nearest_ride = remaining.pop(nearest_idx)
        ordered.append(nearest_ride)
        current_point = location_getter(nearest_ride)
    
    return ordered


# =============================================================================
# Module-level convenience
# =============================================================================

_default_solver: Optional[RouteSolver] = None


def get_route_solver() -> RouteSolver:
    """Get or create the default route solver."""
    global _default_solver
    if _default_solver is None:
        _default_solver = RouteSolver()
    return _default_solver
