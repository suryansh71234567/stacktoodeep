"""
Discount calculation based on time flexibility.
"""

# Base ride cost assumption for savings calculation
BASE_RIDE_COST = 100.0

# Maximum discount percentage
MAX_DISCOUNT_RATIO = 0.30  # 30%

# Flexibility reference value (flex_score at which max discount is reached)
FLEX_REFERENCE = 120.0


def compute_flex_score(buffer_before_min: int, buffer_after_min: int) -> float:
    """
    Compute flexibility score based on time buffers.
    
    The flex score represents how much scheduling flexibility a user offers.
    Higher flexibility enables better pooling and routing opportunities.
    
    Formula: flex_score = (0.6 * buffer_before_min) + (0.4 * buffer_after_min)
    
    Args:
        buffer_before_min: Minutes willing to depart before preferred time
        buffer_after_min: Minutes willing to depart after preferred time
        
    Returns:
        Flexibility score as a float
    """
    flex_score = (0.6 * buffer_before_min) + (0.4 * buffer_after_min)
    return float(flex_score)


def compute_user_savings(flex_score: float) -> float:
    """
    Compute user savings based on flexibility score.
    
    Higher flexibility scores result in greater discounts, up to a maximum
    of 30% of the base ride cost.
    
    Args:
        flex_score: Flexibility score from compute_flex_score()
        
    Returns:
        Absolute savings amount (not percentage)
    """
    # Discount ratio capped at 30%
    discount_ratio = min(MAX_DISCOUNT_RATIO, flex_score / FLEX_REFERENCE)
    
    # Calculate absolute savings based on base ride cost
    savings = BASE_RIDE_COST * discount_ratio
    
    return float(savings)


def compute_total_savings_for_rides(rides_flex_data: list) -> float:
    """
    Compute total savings for a list of rides.
    
    Args:
        rides_flex_data: List of tuples (buffer_before_min, buffer_after_min)
        
    Returns:
        Total savings for all rides
    """
    total_savings = 0.0
    for buffer_before, buffer_after in rides_flex_data:
        flex_score = compute_flex_score(buffer_before, buffer_after)
        total_savings += compute_user_savings(flex_score)
    return total_savings
