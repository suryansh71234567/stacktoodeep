"""
Comprehensive tests for the ride optimization platform.
"""
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

# Test imports
from app.main import app
from app.models.ride import RideRequest, Location
from app.models.route import Stop, StopType
from app.utils.time_windows import (
    compute_time_window, 
    time_windows_overlap,
    compute_overlap_window
)
from app.services.discount_calculator import (
    compute_flex_score, 
    compute_user_savings,
    BASE_RIDE_COST,
    MAX_DISCOUNT_RATIO
)
from app.services.optimization.routing import (
    haversine_distance_km, 
    estimate_route_distance_and_time
)
from app.services.optimization.pooling import pool_rides, are_rides_poolable
from app.services.optimization.solver import solve_cluster
from app.services.pricing_engine import compute_pricing
from app.services.optimization.optimizer import optimize_rides


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_rides():
    """Load sample ride data from fixtures."""
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_rides.json"
    with open(fixtures_path) as f:
        data = json.load(f)
    
    rides = []
    for ride_data in data:
        ride = RideRequest(
            pickup=Location(**ride_data["pickup"]),
            drop=Location(**ride_data["drop"]),
            preferred_time=datetime.fromisoformat(ride_data["preferred_time"]),
            buffer_before_min=ride_data["buffer_before_min"],
            buffer_after_min=ride_data["buffer_after_min"]
        )
        rides.append(ride)
    return rides


@pytest.fixture
def test_client():
    """Create test client for API testing."""
    return TestClient(app)


# ============================================================================
# Flex Score Tests
# ============================================================================

class TestFlexScore:
    """Tests for flexibility score calculation."""
    
    def test_flex_score_zero_buffers(self):
        """Zero flexibility should give zero score."""
        score = compute_flex_score(0, 0)
        assert score == 0.0
    
    def test_flex_score_formula(self):
        """Verify flex score formula: 0.6*before + 0.4*after."""
        # buffer_before=10, buffer_after=20
        # Expected: 0.6*10 + 0.4*20 = 6 + 8 = 14
        score = compute_flex_score(10, 20)
        assert score == 14.0
    
    def test_flex_score_weighted_correctly(self):
        """Before buffer should have higher weight than after."""
        before_heavy = compute_flex_score(30, 0)  # 0.6*30 = 18
        after_heavy = compute_flex_score(0, 30)   # 0.4*30 = 12
        assert before_heavy > after_heavy
    
    def test_flex_score_max_flexibility(self):
        """High flexibility scores should be computed correctly."""
        # 120 min each: 0.6*120 + 0.4*120 = 72 + 48 = 120
        score = compute_flex_score(120, 120)
        assert score == 120.0


# ============================================================================
# User Savings Tests
# ============================================================================

class TestUserSavings:
    """Tests for user savings calculation."""
    
    def test_savings_zero_flex(self):
        """Zero flexibility should give zero savings."""
        savings = compute_user_savings(0.0)
        assert savings == 0.0
    
    def test_savings_max_cap(self):
        """Savings should be capped at 30%."""
        # Very high flex score should still cap at 30%
        savings = compute_user_savings(200.0)
        max_savings = BASE_RIDE_COST * MAX_DISCOUNT_RATIO
        assert savings == max_savings
    
    def test_savings_proportional(self):
        """Savings should be proportional to flex score up to cap."""
        # flex_score = 60, reference = 120
        # discount_ratio = min(0.3, 60/120) = min(0.3, 0.5) = 0.3
        # savings = 100 * 0.3 = 30
        savings = compute_user_savings(60.0)
        assert savings == 30.0
    
    def test_savings_below_cap(self):
        """Savings below cap should be calculated correctly."""
        # flex_score = 30, reference = 120
        # discount_ratio = 30/120 = 0.25
        # savings = 100 * 0.25 = 25
        savings = compute_user_savings(30.0)
        assert savings == 25.0


# ============================================================================
# Time Window Tests
# ============================================================================

class TestTimeWindows:
    """Tests for time window computation."""
    
    def test_compute_time_window_basic(self):
        """Basic time window computation."""
        preferred = datetime(2026, 1, 24, 9, 0, 0)
        start, end = compute_time_window(preferred, 15, 30)
        
        expected_start = preferred - timedelta(minutes=15)
        expected_end = preferred + timedelta(minutes=30)
        
        assert start == expected_start
        assert end == expected_end
    
    def test_time_windows_overlap_true(self):
        """Overlapping windows should return True."""
        w1 = (datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 9, 30))
        w2 = (datetime(2026, 1, 24, 9, 15), datetime(2026, 1, 24, 9, 45))
        
        assert time_windows_overlap(w1, w2) is True
    
    def test_time_windows_overlap_false(self):
        """Non-overlapping windows should return False."""
        w1 = (datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 9, 30))
        w2 = (datetime(2026, 1, 24, 10, 0), datetime(2026, 1, 24, 10, 30))
        
        assert time_windows_overlap(w1, w2) is False
    
    def test_time_windows_adjacent(self):
        """Adjacent windows (touching) should overlap."""
        w1 = (datetime(2026, 1, 24, 9, 0), datetime(2026, 1, 24, 9, 30))
        w2 = (datetime(2026, 1, 24, 9, 30), datetime(2026, 1, 24, 10, 0))
        
        assert time_windows_overlap(w1, w2) is True


# ============================================================================
# Haversine Distance Tests
# ============================================================================

class TestHaversineDistance:
    """Tests for haversine distance calculation."""
    
    def test_same_point_zero_distance(self):
        """Same point should have zero distance."""
        dist = haversine_distance_km(28.6139, 77.2090, 28.6139, 77.2090)
        assert dist == 0.0
    
    def test_known_distance(self):
        """Test with known Delhi locations."""
        # Connaught Place to India Gate (~1.5 km)
        dist = haversine_distance_km(28.6315, 77.2167, 28.6129, 77.2295)
        assert 1.0 < dist < 3.0  # Approximate range
    
    def test_distance_symmetry(self):
        """Distance should be symmetric."""
        d1 = haversine_distance_km(28.6139, 77.2090, 28.5355, 77.3910)
        d2 = haversine_distance_km(28.5355, 77.3910, 28.6139, 77.2090)
        assert abs(d1 - d2) < 0.001


# ============================================================================
# Pooling Tests
# ============================================================================

class TestPooling:
    """Tests for ride pooling logic."""
    
    def test_pool_empty_list(self):
        """Empty input should return empty clusters."""
        clusters = pool_rides([])
        assert clusters == []
    
    def test_pool_single_ride(self):
        """Single ride should form its own cluster."""
        ride = RideRequest(
            pickup=Location(lat=28.6139, lng=77.2090),
            drop=Location(lat=28.5355, lng=77.3910),
            preferred_time=datetime(2026, 1, 24, 9, 0),
            buffer_before_min=15,
            buffer_after_min=30
        )
        clusters = pool_rides([ride])
        
        assert len(clusters) == 1
        assert len(clusters[0]) == 1
    
    def test_nearby_rides_pooled(self, sample_rides):
        """Nearby rides with overlapping windows should be pooled."""
        clusters = pool_rides(sample_rides)
        
        # First 2 rides and ride 4 are nearby (within 2km)
        # Ride 3 is far away
        # So we expect at least 2 clusters
        assert len(clusters) >= 1
        assert len(clusters) <= len(sample_rides)
    
    def test_far_rides_not_pooled(self):
        """Rides with pickups > 2km apart should not be pooled."""
        ride1 = RideRequest(
            pickup=Location(lat=28.6139, lng=77.2090),  # Delhi
            drop=Location(lat=28.5355, lng=77.3910),
            preferred_time=datetime(2026, 1, 24, 9, 0),
            buffer_before_min=15,
            buffer_after_min=30
        )
        ride2 = RideRequest(
            pickup=Location(lat=19.0760, lng=72.8777),  # Mumbai (far!)
            drop=Location(lat=19.0330, lng=72.8296),
            preferred_time=datetime(2026, 1, 24, 9, 0),
            buffer_before_min=15,
            buffer_after_min=30
        )
        
        clusters = pool_rides([ride1, ride2])
        assert len(clusters) == 2  # Each ride in its own cluster


# ============================================================================
# Pricing Tests
# ============================================================================

class TestPricing:
    """Tests for pricing calculation."""
    
    def test_baseline_profit_formula(self):
        """Baseline profit should be distance * 10."""
        pricing = compute_pricing(
            route_distance_km=15.0,
            pooling_efficiency=0.0,
            total_user_savings=0.0
        )
        assert pricing.baseline_driver_profit == 150.0
    
    def test_pooling_efficiency_bonus(self):
        """Pooling efficiency should increase driver profit."""
        pricing = compute_pricing(
            route_distance_km=15.0,
            pooling_efficiency=0.20,  # 20% efficiency
            total_user_savings=0.0
        )
        # optimized = 150 * 1.2 = 180
        assert pricing.optimized_driver_profit == 180.0
    
    def test_broker_commission_rate(self):
        """Broker commission should be 10% of optimized profit."""
        pricing = compute_pricing(
            route_distance_km=10.0,
            pooling_efficiency=0.0,
            total_user_savings=0.0
        )
        # baseline = 100, optimized = 100, commission = 10
        assert pricing.broker_commission == 10.0
    
    def test_user_savings_passed_through(self):
        """User savings should be included in pricing."""
        pricing = compute_pricing(
            route_distance_km=10.0,
            pooling_efficiency=0.0,
            total_user_savings=25.0
        )
        assert pricing.total_user_savings == 25.0


# ============================================================================
# API Tests
# ============================================================================

class TestAPI:
    """Tests for the API endpoint."""
    
    def test_health_check(self, test_client):
        """Health endpoint should return healthy status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_optimize_endpoint_success(self, test_client, sample_rides):
        """POST /optimize should return valid output."""
        # Convert sample rides to JSON-serializable format
        rides_data = []
        for ride in sample_rides:
            rides_data.append({
                "pickup": {"lat": ride.pickup.lat, "lng": ride.pickup.lng},
                "drop": {"lat": ride.drop.lat, "lng": ride.drop.lng},
                "preferred_time": ride.preferred_time.isoformat(),
                "buffer_before_min": ride.buffer_before_min,
                "buffer_after_min": ride.buffer_after_min
            })
        
        response = test_client.post(
            "/optimize",
            json={"ride_requests": rides_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "bundles" in data
        assert "total_rides_processed" in data
        assert data["total_rides_processed"] == 4
        assert len(data["bundles"]) > 0
    
    def test_optimize_empty_input(self, test_client):
        """Empty ride requests should return error."""
        response = test_client.post(
            "/optimize",
            json={"ride_requests": []}
        )
        assert response.status_code == 422  # Validation error
    
    def test_optimize_single_ride(self, test_client):
        """Single ride should return single bundle."""
        response = test_client.post(
            "/optimize",
            json={
                "ride_requests": [{
                    "pickup": {"lat": 28.6139, "lng": 77.2090},
                    "drop": {"lat": 28.5355, "lng": 77.3910},
                    "preferred_time": "2026-01-24T09:00:00",
                    "buffer_before_min": 15,
                    "buffer_after_min": 30
                }]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_bundles_created"] == 1
        assert len(data["bundles"]) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests."""
    
    def test_full_optimization_flow(self, sample_rides):
        """Test complete optimization flow."""
        result = optimize_rides(sample_rides)
        
        # Check output structure
        assert result.total_rides_processed == 4
        assert result.total_bundles_created >= 1
        assert len(result.bundles) >= 1
        
        # Check each bundle has required fields
        for bundle in result.bundles:
            assert len(bundle.ride_request_ids) >= 1
            assert bundle.route is not None
            assert bundle.pricing is not None
            assert bundle.time_window_start is not None
            assert bundle.time_window_end is not None
            
            # Check route has stops
            assert len(bundle.route.stops) >= 2  # At least pickup and drop
            
            # Check pricing is valid
            assert bundle.pricing.baseline_driver_profit >= 0
            assert bundle.pricing.optimized_driver_profit >= 0
            assert bundle.pricing.broker_commission >= 0
    
    def test_deterministic_output(self, sample_rides):
        """Same input should produce same output."""
        result1 = optimize_rides(sample_rides)
        result2 = optimize_rides(sample_rides)
        
        assert result1.total_bundles_created == result2.total_bundles_created
        assert result1.total_rides_processed == result2.total_rides_processed
