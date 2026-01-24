"""
Comprehensive tests for the optimization engine.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from app.models.ride import RideRequest, Location, TimeWindow, RideStatus
from app.models.route import VehicleRoute, Stop
from app.services.optimization.optimizer import OptimizationService
from app.services.optimization.pooling import RidePooler
from app.services.optimization.solver import RouteSolver
from app.services.pricing_engine import PricingEngine
from app.utils.routing import RoutingService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()

@pytest.fixture
def mock_routing_service():
    """Mock RoutingService to avoid external API calls."""
    service = Mock(spec=RoutingService)
    
    # Setup default return values
    service.get_distance.return_value = 5.0 # 5 km
    service.get_duration.return_value = 10.0 # 10 mins
    
    # Mock distance matrix
    async def mock_matrix(sources, destinations):
        # Return a matrix of 10s
        return [[10.0 for _ in destinations] for _ in sources]
    
    service.get_distance_matrix = AsyncMock(side_effect=mock_matrix)
    return service

@pytest.fixture
def sample_rides():
    """Create sample rides for testing."""
    now = datetime.now()
    
    # Ride 1: Delhi Center
    ride1 = RideRequest(
        id=uuid.uuid4(),
        user_id="user1",
        pickup=Location(latitude=28.6139, longitude=77.2090, address="Connaught Place"),
        dropoff=Location(latitude=28.5355, longitude=77.3910, address="Noida Sector 18"),
        time_window=TimeWindow(earliest=now, latest=now + timedelta(minutes=30), preferred=now + timedelta(minutes=15)),
        num_passengers=1,
        status=RideStatus.REQUESTED,
        created_at=now
    )
    
    # Ride 2: Nearby Pickup, overlap time
    ride2 = RideRequest(
        id=uuid.uuid4(),
        user_id="user2",
        pickup=Location(latitude=28.6129, longitude=77.2080, address="Near CP"),
        dropoff=Location(latitude=28.5360, longitude=77.3920, address="Noida Sector 16"),
        time_window=TimeWindow(earliest=now + timedelta(minutes=5), latest=now + timedelta(minutes=35), preferred=now + timedelta(minutes=20)),
        num_passengers=1,
        status=RideStatus.REQUESTED,
        created_at=now
    )
    
    # Ride 3: Far away (Mumbai)
    ride3 = RideRequest(
        id=uuid.uuid4(),
        user_id="user3",
        pickup=Location(latitude=19.0760, longitude=72.8777, address="Mumbai"),
        dropoff=Location(latitude=19.0330, longitude=72.8296, address="Bandra"),
        time_window=TimeWindow(earliest=now, latest=now + timedelta(minutes=30), preferred=now + timedelta(minutes=15)),
        num_passengers=1,
        status=RideStatus.REQUESTED,
        created_at=now
    )
    
    return [ride1, ride2, ride3]

@pytest.fixture
def optimization_service(mock_db_session, mock_routing_service):
    """Create OptimizationService with mocks."""
    pooler = RidePooler(routing_service=mock_routing_service)
    # Using real solver but with mocked routing is safer for unit tests
    # But RouteSolver uses OR-Tools, which we might want to test logic of
    solver = RouteSolver(routing_service=mock_routing_service, time_limit_seconds=1)
    pricing = PricingEngine()
    
    return OptimizationService(
        routing_service=mock_routing_service,
        pricing_engine=pricing,
        pooler=pooler,
        solver=solver
    )


# ============================================================================
# Test Cases
# ============================================================================

@pytest.mark.asyncio
async def test_simple_pool_two_rides(optimization_service, sample_rides, mock_routing_service):
    """
    Test 1: Simple pooling of two compatible rides.
    Input: 2 rides with overlapping time windows, same direction (ride1, ride2)
    Expected: 1 vehicle route with 2 rides
    """
    rides = [sample_rides[0], sample_rides[1]] # CP and Near CP
    
    # Mock RouteSolver to return a valid route
    # We patch the internal solver call to avoid complex OR-Tools dependency in unit test if strictly needed,
    # but here we rely on the logic. 
    # Since we mocked routing service matrix to always return 10, the logic should see them as close.
    # However, RidePooler geodistance check uses haversine on actual lat/lon.
    # ride1 and ride2 are very close (~0.1km).
    
    output = await optimization_service.optimize(rides)
    
    assert output.status == "success"
    assert len(output.routes) == 1
    
    route = output.routes[0]
    # Check both rides are in the route
    ride_ids = set(stop.ride_id for stop in route.stops)
    # Convert ride IDs to string for comparison if they are UUIDs
    assert str(rides[0].id) in ride_ids
    assert str(rides[1].id) in ride_ids
    
    # Check capacity used
    assert route.capacity_used == 2

@pytest.mark.asyncio
async def test_incompatible_time_windows(optimization_service, sample_rides):
    """
    Test 2: Rides with incompatible time windows.
    Input: 2 rides with non-overlapping time windows
    Expected: 2 separate vehicle routes
    """
    now = datetime.now()
    ride1 = sample_rides[0]
    
    # Create incompatible ride (1 hour later)
    ride4 = RideRequest(
        id=uuid.uuid4(),
        user_id="user4",
        pickup=ride1.pickup,
        dropoff=ride1.dropoff,
        time_window=TimeWindow(
            earliest=now + timedelta(hours=2), 
            latest=now + timedelta(hours=3),
            preferred=now + timedelta(hours=2, minutes=30)
        ),
        num_passengers=1,
        status=RideStatus.REQUESTED,
        created_at=now
    )
    
    output = await optimization_service.optimize([ride1, ride4])
    
    assert output.status == "success"
    # Should stay separate because times don't overlap
    assert len(output.routes) == 2
    assert output.metrics.vehicles_used == 2 # 2 vehicles for 2 rides

@pytest.mark.asyncio
async def test_capacity_constraint(optimization_service, sample_rides):
    """
    Test 3: Capacity constraint.
    Input: 3 rides, each with 2 passengers
    Expected: At least 2 vehicles (capacity = 4)
    """
    now = datetime.now()
    loc1 = sample_rides[0].pickup
    loc2 = sample_rides[0].dropoff
    
    # 3 rides identical but 2 passengers each
    rides = []
    for i in range(3):
        rides.append(RideRequest(
            id=uuid.uuid4(),
            user_id=f"user_cap_{i}",
            pickup=loc1,
            dropoff=loc2,
            time_window=TimeWindow(earliest=now, latest=now + timedelta(minutes=60), preferred=now + timedelta(minutes=30)),
            num_passengers=2, # 2 * 3 = 6 passengers total
            status=RideStatus.REQUESTED,
            created_at=now
        ))
        
    output = await optimization_service.optimize(rides)
    
    assert output.status == "success"
    # Total passengers = 6. Max capacity = 4.
    # Must use at least 2 vehicles.
    assert len(output.routes) >= 2
    
    # Verify no vehicle exceeds capacity
    for route in output.routes:
        load = 0
        max_load = 0
        for stop in route.stops:
            if stop.type == "pickup":
                load += stop.num_passengers
            else:
                load -= stop.num_passengers
            max_load = max(max_load, load)
        assert max_load <= 4

@pytest.mark.asyncio
async def test_precedence_constraint(optimization_service, sample_rides):
    """
    Test 4: Pickup must occur before dropoff.
    Input: 1 ride
    Verify: Pickup occurs before dropoff in route
    """
    ride = sample_rides[0]
    output = await optimization_service.optimize([ride])
    
    assert len(output.routes) == 1
    route = output.routes[0]
    
    stops = route.stops
    # Should only be 2 stops for 1 ride
    assert len(stops) == 2
    assert stops[0].type == "pickup"
    assert stops[1].type == "dropoff"
    assert stops[0].ride_id == str(ride.id)
    assert stops[1].ride_id == str(ride.id)

@pytest.mark.asyncio
async def test_pricing_discount(optimization_service, sample_rides):
    """
    Test 5: Pooled rides get validation of cost.
    Verify: Pricing engine is called and metrics saved.
    """
    rides = [sample_rides[0], sample_rides[1]]
    output = await optimization_service.optimize(rides)
    
    assert len(output.routes) == 1
    route = output.routes[0]
    
    # Check revenue is calculated
    assert route.revenue > 0
    
    # Check savings calculated
    assert output.total_savings >= 0
    
    # If using Mock pricing engine, we could verify exact calls, 
    # but here we verify the output structure contains pricing info.

@pytest.mark.asyncio
async def test_optimization_timeout(optimization_service, sample_rides):
    """
    Test 6: Optimization completes. 
    (Hard to force actual timeout in unit test without sleep injection, 
    so we assume it completes and check structure).
    """
    # Just run on sample rides
    output = await optimization_service.optimize(sample_rides)
    
    # Should return success or partial
    assert output.status in ["success", "partial"]
    assert output.optimization_time_seconds >= 0

@pytest.mark.asyncio
async def test_geographic_pooling(optimization_service, sample_rides):
    """
    Test 7: Geographic proximity logic.
    Input: 3 rides - 2 close (Delhi), 1 far (Mumbai)
    Expected: First 2 pooled, third separate
    """
    # Rides: 0=Delhi, 1=Delhi, 2=Mumbai
    output = await optimization_service.optimize(sample_rides)
    
    # Should be 2 routes: 1 for Delhi pair, 1 for Mumbai
    assert len(output.routes) == 2
    
    # Find the Mumbai route
    mumbai_route = next(r for r in output.routes if r.stops[0].ride_id == str(sample_rides[2].id))
    assert len(mumbai_route.stops) == 2 # Only ride3
    
    # Find Delhi route
    delhi_route = next(r for r in output.routes if r.stops[0].ride_id != str(sample_rides[2].id))
    assert len(delhi_route.stops) == 4 # ride1 + ride2 (2 stops each)

@pytest.mark.asyncio
async def test_detour_limit(optimization_service, sample_rides, mock_routing_service):
    """
    Test 8: Detour limit prevents pooling.
    Input: 2 rides where pooling would exceed max_detour
    Expected: Rides not pooled
    """
    ride1 = sample_rides[0]
    ride2 = sample_rides[1]

    # RidePooler uses _estimate_detour_sync which uses geometric math.
    # To test the logic that "if detour > max, don't pool", we can patch the internal estimator
    # or use coordinates that naturally cause a large detour relative to solo.
    
    # We choose to patch the estimator to simulate a high detour situation 
    # (e.g. traffic or road layout that geometric dist doesn't catch, but here we force the value)
    
    # We need to patch it on the `pooler` instance inside `optimization_service`
    with patch.object(optimization_service.pooler, '_estimate_detour_sync', return_value=120.0):
        output = await optimization_service.optimize([ride1, ride2])
        
        # Should be 2 separate routes because detour (120) > max (15)
        assert len(output.routes) == 2
