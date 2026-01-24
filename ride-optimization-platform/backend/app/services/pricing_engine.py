"""
Pricing Engine for Ride Optimization Platform.

This module calculates ride costs, pooling discounts, driver earnings,
and system-wide savings from optimization.

Pricing Philosophy:
- Base pricing covers operational costs (distance + time)
- Pooling discounts incentivize ride-sharing (saves everyone money)
- Platform fee sustains the marketplace
- Driver earnings ensure fair compensation
"""
from typing import Dict, List, Optional

from app.models.ride import RideRequest
from app.models.route import VehicleRoute
from app.models.pricing import PricingBreakdown


# =============================================================================
# Pricing Constants (All in $ / INR as appropriate)
# =============================================================================

# Base fare constants
BASE_FARE = 3.00           # Fixed cost for any ride ($3 or ₹50)
PER_KM_RATE = 1.50         # Cost per kilometer ($1.50 or ₹12)
PER_MINUTE_RATE = 0.30     # Cost per minute ($0.30 or ₹2)

# Pooling discount percentages by number of riders
POOL_DISCOUNTS = {
    1: 0.00,    # Solo ride - no discount
    2: 0.20,    # 2 riders - 20% discount
    3: 0.30,    # 3 riders - 30% discount
    4: 0.40,    # 4+ riders - 40% discount (max discount)
}

# Platform fee (percentage of gross revenue)
PLATFORM_FEE_RATE = 0.15   # 15%

# Legacy constants for backward compatibility
RATE_PER_KM = 10.0
BROKER_COMMISSION_RATE = 0.10


# =============================================================================
# PricingEngine Class
# =============================================================================

class PricingEngine:
    """
    Calculates ride pricing, discounts, and earnings.
    
    Handles all pricing-related calculations including:
    - Base ride pricing (distance + time based)
    - Pooling discounts (incentivizes ride-sharing)
    - Driver earnings (after platform fee)
    - System-wide savings estimation
    
    Example:
        >>> engine = PricingEngine()
        >>> base_price = engine.calculate_base_price(distance_km=10, duration_minutes=25)
        >>> print(f"Base price: ${base_price:.2f}")
        Base price: $25.50
        >>> 
        >>> pooled_price = engine.calculate_pooled_price(base_price, num_riders=3)
        >>> print(f"Pooled price: ${pooled_price:.2f} (30% off)")
        Pooled price: $17.85 (30% off)
    """
    
    def __init__(
        self,
        base_fare: float = BASE_FARE,
        per_km_rate: float = PER_KM_RATE,
        per_minute_rate: float = PER_MINUTE_RATE,
        platform_fee_rate: float = PLATFORM_FEE_RATE,
    ):
        """
        Initialize the pricing engine with configurable rates.
        
        Args:
            base_fare: Fixed base cost for any ride
            per_km_rate: Cost per kilometer
            per_minute_rate: Cost per minute of travel
            platform_fee_rate: Platform commission (0.0 to 1.0)
        """
        self.base_fare = base_fare
        self.per_km_rate = per_km_rate
        self.per_minute_rate = per_minute_rate
        self.platform_fee_rate = platform_fee_rate
    
    def calculate_base_price(
        self,
        distance_km: float,
        duration_minutes: float
    ) -> float:
        """
        Calculate base price for a ride (before any discounts).
        
        Formula:
            price = base_fare + (distance_km × per_km_rate) + (duration_minutes × per_minute_rate)
        
        Example:
            For a 10km ride taking 25 minutes:
            price = $3.00 + (10 × $1.50) + (25 × $0.30)
                  = $3.00 + $15.00 + $7.50
                  = $25.50
        
        Args:
            distance_km: Route distance in kilometers
            duration_minutes: Travel time in minutes
            
        Returns:
            Base price in currency units (before discounts)
            
        Example:
            >>> engine = PricingEngine()
            >>> price = engine.calculate_base_price(10, 25)
            >>> print(f"${price:.2f}")
            $25.50
        """
        if distance_km < 0 or duration_minutes < 0:
            raise ValueError("Distance and duration must be non-negative")
        
        price = (
            self.base_fare +
            (distance_km * self.per_km_rate) +
            (duration_minutes * self.per_minute_rate)
        )
        
        return round(price, 2)
    
    def calculate_pooled_price(
        self,
        base_price: float,
        num_riders_in_pool: int
    ) -> float:
        """
        Apply pooling discount based on number of riders sharing the vehicle.
        
        Discount schedule:
            - 1 rider (solo): 0% discount
            - 2 riders: 20% discount
            - 3 riders: 30% discount
            - 4+ riders: 40% discount (maximum)
        
        Each rider in the pool gets the SAME discounted price.
        This means the driver earns MORE per km while riders pay LESS.
        
        Example:
            Base price: $25.50
            3 riders sharing: 30% discount
            Each rider pays: $25.50 × (1 - 0.30) = $17.85
            Driver receives: $17.85 × 3 = $53.55 (vs $25.50 for solo)
        
        Args:
            base_price: Original price before discount
            num_riders_in_pool: Number of riders sharing the vehicle (1-4+)
            
        Returns:
            Discounted price per rider
            
        Example:
            >>> engine = PricingEngine()
            >>> pooled = engine.calculate_pooled_price(25.50, 3)
            >>> print(f"${pooled:.2f}")
            $17.85
        """
        if base_price < 0:
            raise ValueError("Base price must be non-negative")
        if num_riders_in_pool < 1:
            raise ValueError("Number of riders must be at least 1")
        
        # Get discount rate (cap at 4 riders for max discount)
        riders_key = min(num_riders_in_pool, 4)
        discount_rate = POOL_DISCOUNTS.get(riders_key, 0.40)
        
        discounted_price = base_price * (1 - discount_rate)
        
        return round(discounted_price, 2)
    
    def calculate_discount_percentage(
        self,
        original_price: float,
        discounted_price: float
    ) -> float:
        """
        Calculate the percentage saved.
        
        Formula:
            savings_percent = ((original - discounted) / original) × 100
        
        Args:
            original_price: Price before discount
            discounted_price: Price after discount
            
        Returns:
            Percentage saved (0-100)
            
        Example:
            >>> engine = PricingEngine()
            >>> pct = engine.calculate_discount_percentage(25.50, 17.85)
            >>> print(f"{pct:.1f}%")
            30.0%
        """
        if original_price <= 0:
            return 0.0
        if discounted_price < 0:
            raise ValueError("Discounted price cannot be negative")
        if discounted_price > original_price:
            return 0.0  # No discount (or price increased)
        
        savings_percent = ((original_price - discounted_price) / original_price) * 100
        
        return round(savings_percent, 2)
    
    def calculate_driver_earnings(self, route: VehicleRoute) -> Dict:
        """
        Calculate driver earnings for a complete route.
        
        Takes all rides in the route, sums their fares,
        and deducts the platform fee.
        
        Earnings breakdown:
            - gross_revenue: Total fares from all riders
            - platform_fee: 15% commission to platform
            - net_earnings: What driver takes home
            - earnings_per_km: Efficiency metric
        
        Args:
            route: VehicleRoute with stops and distance
            
        Returns:
            Dict with:
            - gross_revenue: Total fares collected
            - platform_fee: Platform's cut (15%)
            - net_earnings: Driver's take-home
            - earnings_per_km: Efficiency (net / distance)
            
        Example:
            >>> engine = PricingEngine()
            >>> earnings = engine.calculate_driver_earnings(route)
            >>> print(f"Net: ${earnings['net_earnings']:.2f}")
        """
        # Calculate gross revenue based on route metrics
        num_riders = len(set(stop.ride_id for stop in route.stops)) // 2  # Divide by 2 (pickup + dropoff)
        if num_riders == 0:
            num_riders = max(1, len(route.stops) // 2)
        
        # Base revenue from route
        base_price = self.calculate_base_price(
            route.total_distance_km,
            route.total_duration_minutes
        )
        
        # Apply pooling - each rider pays pooled price
        pooled_price = self.calculate_pooled_price(base_price, num_riders)
        gross_revenue = pooled_price * num_riders
        
        # Calculate fees and net
        platform_fee = gross_revenue * self.platform_fee_rate
        net_earnings = gross_revenue - platform_fee
        
        # Earnings efficiency
        earnings_per_km = 0.0
        if route.total_distance_km > 0:
            earnings_per_km = net_earnings / route.total_distance_km
        
        return {
            "gross_revenue": round(gross_revenue, 2),
            "platform_fee": round(platform_fee, 2),
            "net_earnings": round(net_earnings, 2),
            "earnings_per_km": round(earnings_per_km, 2),
        }
    
    def estimate_savings(
        self,
        rides: List[RideRequest],
        routes: List[VehicleRoute]
    ) -> Dict:
        """
        Estimate system-wide savings from pooling optimization.
        
        Compares what riders would pay individually (solo) vs
        what they pay with optimized pooling.
        
        Args:
            rides: List of ride requests
            routes: Optimized routes (may be fewer than rides due to pooling)
            
        Returns:
            Dict with:
            - total_solo_cost: Cost if all rides were separate
            - total_pooled_cost: Cost with optimization
            - total_savings: Money saved
            - average_savings_per_ride: Per-ride savings
            
        Example:
            >>> engine = PricingEngine()
            >>> savings_info = engine.estimate_savings(rides, routes)
            >>> print(f"Total saved: ${savings_info['total_savings']:.2f}")
        """
        if not rides:
            return {
                "total_solo_cost": 0.0,
                "total_pooled_cost": 0.0,
                "total_savings": 0.0,
                "average_savings_per_ride": 0.0,
            }
        
        # Calculate solo costs (hypothetical - each ride alone)
        total_solo_cost = 0.0
        for ride in rides:
            # Estimate distance from pickup to dropoff (simplified)
            # In real implementation, would use routing service
            lat_diff = abs(ride.dropoff.latitude - ride.pickup.latitude)
            lon_diff = abs(ride.dropoff.longitude - ride.pickup.longitude)
            estimated_distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # Approx km
            estimated_duration = estimated_distance * 3  # ~20 km/h in city
            
            solo_price = self.calculate_base_price(estimated_distance, estimated_duration)
            total_solo_cost += solo_price
        
        # Calculate pooled costs (actual from routes)
        total_pooled_cost = 0.0
        for route in routes:
            num_riders = max(1, len(route.stops) // 2)
            base_price = self.calculate_base_price(
                route.total_distance_km,
                route.total_duration_minutes
            )
            pooled_price = self.calculate_pooled_price(base_price, num_riders)
            total_pooled_cost += pooled_price * num_riders
        
        # Calculate savings
        total_savings = max(0, total_solo_cost - total_pooled_cost)
        avg_savings = total_savings / len(rides) if rides else 0.0
        
        return {
            "total_solo_cost": round(total_solo_cost, 2),
            "total_pooled_cost": round(total_pooled_cost, 2),
            "total_savings": round(total_savings, 2),
            "average_savings_per_ride": round(avg_savings, 2),
        }


# =============================================================================
# Legacy Function (Backward Compatibility)
# =============================================================================

def compute_pricing(
    route_distance_km: float,
    pooling_efficiency: float,
    total_user_savings: float
) -> PricingBreakdown:
    """
    Compute bundle-level economics (legacy function).
    
    Kept for backward compatibility with existing code.
    
    Args:
        route_distance_km: Total route distance in kilometers
        pooling_efficiency: Efficiency gain from pooling (0.0 to 1.0)
        total_user_savings: Total savings for all users in the bundle
        
    Returns:
        PricingBreakdown with all economic metrics
    """
    # Calculate baseline driver profit
    baseline_driver_profit = route_distance_km * RATE_PER_KM
    
    # Apply pooling efficiency bonus
    optimized_driver_profit = baseline_driver_profit * (1 + pooling_efficiency)
    
    # Calculate broker commission
    broker_commission = optimized_driver_profit * BROKER_COMMISSION_RATE
    
    return PricingBreakdown(
        baseline_driver_profit=round(baseline_driver_profit, 2),
        optimized_driver_profit=round(optimized_driver_profit, 2),
        total_user_savings=round(total_user_savings, 2),
        broker_commission=round(broker_commission, 2),
        pooling_efficiency=round(pooling_efficiency, 4)
    )


# =============================================================================
# Module-level convenience
# =============================================================================

# Default engine instance
_default_engine: Optional[PricingEngine] = None


def get_pricing_engine() -> PricingEngine:
    """Get or create the default pricing engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = PricingEngine()
    return _default_engine
