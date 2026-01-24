"""
Discount Engine.
Converts time flexibility into economic value.
"""


def compute_flex_score(buffer_before: int, buffer_after: int) -> float:
    """
    Compute flexibility score based on user's time buffers.
    
    Higher buffers = more flexibility = higher score.
    
    Formula: flex_score = 0.6 * buffer_before + 0.4 * buffer_after
    
    Args:
        buffer_before: Minutes of flexibility before preferred time
        buffer_after: Minutes of flexibility after preferred time
    
    Returns:
        Flexibility score (unbounded positive float)
    """
    flex_score = 0.6 * buffer_before + 0.4 * buffer_after
    return float(flex_score)


def compute_user_savings(flex_score: float, base_ride_cost: float = 100.0) -> float:
    """
    Compute user savings based on flexibility score.
    
    Maximum savings is 30% of base ride cost.
    Savings percentage = min(0.3, flex_score / 120)
    
    Args:
        flex_score: User's flexibility score
        base_ride_cost: Base cost of the ride (default: 100)
    
    Returns:
        Absolute savings value
    """
    # Maximum 30% savings
    savings_percentage = min(0.3, flex_score / 120.0)
    savings = base_ride_cost * savings_percentage
    return float(savings)
