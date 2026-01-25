"""
Tests for the Bidding Orchestration Module.

Tests cover:
- D5: Pre-Bidding Data Builder
- D6: Bidding Lifecycle Controller
- D7: Post-Bidding Data Distributor
- Utils: Coupon generation, timestamp helpers
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.services.bidding import (
    # Types
    PreBiddingPayload,
    WinningBid,
    CompanyPayload,
    UserPayload,
    # Utils
    generate_coupon_code,
    parse_iso_datetime,
    get_earliest_datetime,
    # D5
    build_pre_bidding_payload,
    # D6
    BiddingPhase,
    start_bidding,
    transition_to_reveal,
    end_bidding,
    select_winner,
    get_bidding_state,
    set_blockchain_adapter,
    reset_state,
    # D7
    build_company_payload,
    build_user_payload,
    distribute_post_bidding_data,
    set_notification_services,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_bundle():
    """Standard RideBundle for testing."""
    return {
        "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
        "route": "pickup_user1->pickup_user2->drop_user1->drop_user2",
        "users": [
            {
                "user_id": "user_001",
                "pickup_location": {"lat": 28.61, "lng": 77.20},
                "pickup_time": "2026-01-24T09:00:00",
                "drop_location": {"lat": 28.53, "lng": 77.39},
                "drop_time": "2026-01-24T09:30:00"
            },
            {
                "user_id": "user_002",
                "pickup_location": {"lat": 28.62, "lng": 77.21},
                "pickup_time": "2026-01-24T09:05:00",
                "drop_location": {"lat": 28.54, "lng": 77.40},
                "drop_time": "2026-01-24T09:35:00"
            }
        ],
        "distance": 15.5,
        "duration": 31.0,
        "cost_without_optimization": 200.0,
        "optimized_cost": 155.0
    }


@pytest.fixture
def sample_winner():
    """Standard winning bid for testing."""
    return {
        "company_id": "company_001",
        "bid_value": 165.0
    }


@pytest.fixture
def mock_blockchain_adapter():
    """Mock blockchain adapter."""
    adapter = MagicMock()
    adapter.start_commit = MagicMock()
    adapter.start_reveal = MagicMock()
    adapter.fetch_bids = MagicMock(return_value=[
        {"company_id": "company_001", "bid_value": 165.0},
        {"company_id": "company_002", "bid_value": 150.0},
    ])
    # finalize_auction must return dict with winner info
    adapter.finalize_auction = MagicMock(return_value={
        "winner": "company_001",
        "winningBid": 165000000000000000000,  # 165.0 ETH in wei
        "finalized": True
    })
    return adapter


@pytest.fixture(autouse=True)
def reset_bidding_state():
    """Reset bidding state before each test."""
    reset_state()
    yield
    reset_state()


# =============================================================================
# Utils Tests
# =============================================================================

class TestGenerateCouponCode:
    """Tests for coupon code generation."""
    
    def test_deterministic_output(self):
        """Same inputs should produce same output."""
        code1 = generate_coupon_code("bundle_123", "company_456")
        code2 = generate_coupon_code("bundle_123", "company_456")
        assert code1 == code2
    
    def test_different_bundles_different_codes(self):
        """Different bundles should produce different codes."""
        code1 = generate_coupon_code("bundle_123", "company_456")
        code2 = generate_coupon_code("bundle_789", "company_456")
        assert code1 != code2
    
    def test_different_companies_different_codes(self):
        """Different companies should produce different codes."""
        code1 = generate_coupon_code("bundle_123", "company_456")
        code2 = generate_coupon_code("bundle_123", "company_789")
        assert code1 != code2
    
    def test_format(self):
        """Code should have RIDE- prefix and 8 hex chars."""
        code = generate_coupon_code("bundle_123", "company_456")
        assert code.startswith("RIDE-")
        assert len(code) == 13  # "RIDE-" + 8 chars


class TestParseDatetime:
    """Tests for datetime parsing."""
    
    def test_iso_format(self):
        """Should parse standard ISO format."""
        result = parse_iso_datetime("2026-01-24T09:00:00")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 24
        assert result.hour == 9
    
    def test_datetime_passthrough(self):
        """Should pass through datetime objects."""
        dt = datetime(2026, 1, 24, 9, 0, 0)
        result = parse_iso_datetime(dt)
        assert result == dt
    
    def test_with_timezone(self):
        """Should handle timezone suffix."""
        result = parse_iso_datetime("2026-01-24T09:00:00Z")
        assert result.year == 2026


class TestGetEarliestDatetime:
    """Tests for earliest datetime selection."""
    
    def test_finds_earliest(self):
        """Should return earliest datetime."""
        datetimes = [
            "2026-01-24T10:00:00",
            "2026-01-24T09:00:00",
            "2026-01-24T11:00:00",
        ]
        result = get_earliest_datetime(datetimes)
        assert result.hour == 9
    
    def test_empty_list_raises(self):
        """Should raise on empty list."""
        with pytest.raises(ValueError):
            get_earliest_datetime([])


# =============================================================================
# D5: Pre-Bidding Data Builder Tests
# =============================================================================

class TestBuildPreBiddingPayload:
    """Tests for pre-bidding payload builder."""
    
    def test_correct_output_shape(self, sample_bundle):
        """Should return correct shape."""
        result = build_pre_bidding_payload(sample_bundle)
        
        assert "bundle_id" in result
        assert "time" in result
        assert "duration" in result
        assert "distance" in result
        assert "max_bidding_price" in result
    
    def test_extracts_earliest_time(self, sample_bundle):
        """Should use earliest pickup time."""
        result = build_pre_bidding_payload(sample_bundle)
        # First user has 09:00, second has 09:05
        assert "09:00:00" in result['time']
    
    def test_calculates_max_bidding_price(self, sample_bundle):
        """Should calculate 90% of cost_without_optimization."""
        result = build_pre_bidding_payload(sample_bundle)
        # 200.0 * 0.9 = 180.0
        assert result['max_bidding_price'] == 180.0
    
    def test_preserves_distance_duration(self, sample_bundle):
        """Should preserve distance and duration."""
        result = build_pre_bidding_payload(sample_bundle)
        assert result['distance'] == 15.5
        assert result['duration'] == 31.0
    
    def test_hides_user_details(self, sample_bundle):
        """Should not include user details."""
        result = build_pre_bidding_payload(sample_bundle)
        assert "users" not in result
        assert "route" not in result
    
    def test_missing_field_raises(self):
        """Should raise on missing required field."""
        bundle = {"bundle_id": "test"}
        with pytest.raises(KeyError):
            build_pre_bidding_payload(bundle)
    
    def test_empty_users_raises(self, sample_bundle):
        """Should raise on empty users list."""
        sample_bundle['users'] = []
        with pytest.raises(ValueError):
            build_pre_bidding_payload(sample_bundle)


# =============================================================================
# D6: Bidding Lifecycle Controller Tests
# =============================================================================

class TestBiddingLifecycle:
    """Tests for bidding lifecycle controller."""
    
    def test_start_bidding_creates_state(self):
        """Starting bidding should create state."""
        start_bidding("bundle_123")
        state = get_bidding_state("bundle_123")
        
        assert state is not None
        assert state['phase'] == BiddingPhase.COMMIT
    
    def test_start_bidding_calls_adapter(self, mock_blockchain_adapter):
        """Should call blockchain adapter."""
        set_blockchain_adapter(mock_blockchain_adapter)
        start_bidding("bundle_123")
        
        mock_blockchain_adapter.start_commit.assert_called_once_with("bundle_123")
    
    def test_double_start_raises(self):
        """Starting twice should raise."""
        start_bidding("bundle_123")
        with pytest.raises(ValueError):
            start_bidding("bundle_123")
    
    def test_transition_to_reveal(self, mock_blockchain_adapter):
        """Should transition to REVEAL phase."""
        set_blockchain_adapter(mock_blockchain_adapter)
        start_bidding("bundle_123")
        transition_to_reveal("bundle_123")
        
        state = get_bidding_state("bundle_123")
        assert state['phase'] == BiddingPhase.REVEAL
    
    def test_transition_without_commit_raises(self):
        """Transitioning without COMMIT should raise."""
        with pytest.raises(ValueError):
            transition_to_reveal("bundle_123")
    
    def test_end_bidding_selects_winner(self, mock_blockchain_adapter):
        """Ending should select and return winner."""
        set_blockchain_adapter(mock_blockchain_adapter)
        start_bidding("bundle_123")
        
        winner = end_bidding("bundle_123")
        
        assert winner['company_id'] == "company_001"
        assert winner['bid_value'] == 165.0
    
    def test_end_bidding_finalizes_state(self, mock_blockchain_adapter):
        """Ending should set FINALIZED state."""
        set_blockchain_adapter(mock_blockchain_adapter)
        start_bidding("bundle_123")
        end_bidding("bundle_123")
        
        state = get_bidding_state("bundle_123")
        assert state['phase'] == BiddingPhase.FINALIZED


class TestSelectWinner:
    """Tests for winner selection."""
    
    def test_selects_highest_bid(self, mock_blockchain_adapter):
        """Should select highest bid value."""
        set_blockchain_adapter(mock_blockchain_adapter)
        start_bidding("bundle_123")
        
        winner = select_winner("bundle_123")
        
        assert winner['company_id'] == "company_001"
        assert winner['bid_value'] == 165.0
    
    def test_no_bids_raises(self):
        """Should raise if no bids found."""
        adapter = MagicMock()
        adapter.fetch_bids = MagicMock(return_value=[])
        set_blockchain_adapter(adapter)
        start_bidding("bundle_123")
        
        with pytest.raises(ValueError):
            select_winner("bundle_123")


# =============================================================================
# D7: Post-Bidding Data Distributor Tests
# =============================================================================

class TestBuildCompanyPayload:
    """Tests for company payload builder."""
    
    def test_includes_route(self, sample_bundle, sample_winner):
        """Should include exact route."""
        result = build_company_payload(sample_bundle, sample_winner)
        assert result.exact_route == sample_bundle['route']
    
    def test_includes_all_pickup_points(self, sample_bundle, sample_winner):
        """Should include all pickup points."""
        result = build_company_payload(sample_bundle, sample_winner)
        assert len(result.pickup_points) == 2
    
    def test_includes_all_drop_points(self, sample_bundle, sample_winner):
        """Should include all drop points."""
        result = build_company_payload(sample_bundle, sample_winner)
        assert len(result.drop_points) == 2
    
    def test_includes_user_ids(self, sample_bundle, sample_winner):
        """Should include user IDs."""
        result = build_company_payload(sample_bundle, sample_winner)
        assert "user_001" in result.user_ids
        assert "user_002" in result.user_ids
    
    def test_includes_coupon_code(self, sample_bundle, sample_winner):
        """Should include coupon code."""
        result = build_company_payload(sample_bundle, sample_winner)
        assert result.coupon_code.startswith("RIDE-")


class TestBuildUserPayload:
    """Tests for user payload builder."""
    
    def test_includes_coupon(self, sample_bundle):
        """Should include coupon code."""
        user = sample_bundle['users'][0]
        result = build_user_payload(user, "RIDE-12345678")
        assert result.coupon_code == "RIDE-12345678"
    
    def test_includes_pickup_time(self, sample_bundle):
        """Should include pickup time."""
        user = sample_bundle['users'][0]
        result = build_user_payload(user, "RIDE-12345678")
        assert result.pickup_time.hour == 9
    
    def test_includes_pickup_location(self, sample_bundle):
        """Should include pickup location."""
        user = sample_bundle['users'][0]
        result = build_user_payload(user, "RIDE-12345678")
        assert result.pickup_location.lat == 28.61


class TestDistributePostBiddingData:
    """Tests for full distribution flow."""
    
    def test_returns_company_payload(self, sample_bundle, sample_winner):
        """Should return company payload."""
        result = distribute_post_bidding_data(sample_bundle, sample_winner)
        assert isinstance(result['company_payload'], CompanyPayload)
    
    def test_returns_user_payloads(self, sample_bundle, sample_winner):
        """Should return user payloads."""
        result = distribute_post_bidding_data(sample_bundle, sample_winner)
        assert len(result['user_payloads']) == 2
        assert all(isinstance(p, UserPayload) for p in result['user_payloads'])
    
    def test_same_coupon_for_all(self, sample_bundle, sample_winner):
        """Company and users should get same coupon."""
        result = distribute_post_bidding_data(sample_bundle, sample_winner)
        
        company_coupon = result['company_payload'].coupon_code
        for user_payload in result['user_payloads']:
            assert user_payload.coupon_code == company_coupon
    
    def test_calls_notification_services(self, sample_bundle, sample_winner):
        """Should call notification services if configured."""
        company_service = MagicMock()
        user_service = MagicMock()
        set_notification_services(company_service, user_service)
        
        result = distribute_post_bidding_data(sample_bundle, sample_winner)
        
        assert result['notifications_sent'] is True
        company_service.send.assert_called_once()
        assert user_service.send.call_count == 2


# =============================================================================
# Type Validation Tests
# =============================================================================

class TestTypes:
    """Tests for type definitions."""
    
    def test_pre_bidding_payload_validation(self):
        """PreBiddingPayload should validate correctly."""
        payload = PreBiddingPayload(
            bundle_id="test-123",
            time=datetime.now(),
            duration=30.0,
            distance=15.0,
            max_bidding_price=180.0
        )
        assert payload.bundle_id == "test-123"
    
    def test_winning_bid_validation(self):
        """WinningBid should validate correctly."""
        bid = WinningBid(company_id="company-1", bid_value=150.0)
        assert bid.company_id == "company-1"
    
    def test_negative_duration_rejected(self):
        """Should reject negative duration."""
        with pytest.raises(ValueError):
            PreBiddingPayload(
                bundle_id="test",
                time=datetime.now(),
                duration=-1.0,
                distance=15.0,
                max_bidding_price=180.0
            )
