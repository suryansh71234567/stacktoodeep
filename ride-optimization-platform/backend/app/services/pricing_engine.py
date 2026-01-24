"""
Pricing engine for ride bundles.
"""
from app.models.pricing import PricingBreakdown


# Rate per kilometer for driver profit
RATE_PER_KM = 10.0

# Broker commission percentage
BROKER_COMMISSION_RATE = 0.10  # 10%


def compute_pricing(
    route_distance_km: float,
    pooling_efficiency: float,
    total_user_savings: float
) -> PricingBreakdown:
    """
    Compute bundle-level economics.
    
    Pricing logic:
    - baseline_driver_profit = route_distance_km * 10
    - optimized_driver_profit = baseline * (1 + pooling_efficiency)
    - broker_commission = 10% of optimized_driver_profit
    
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
