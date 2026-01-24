"""
Time-related utility functions.
"""

from datetime import datetime, timedelta
from typing import Tuple


def compute_time_window(
    preferred_time: datetime,
    buffer_before_min: int,
    buffer_after_min: int
) -> Tuple[datetime, datetime]:
    """
    Compute the acceptable time window for a ride request.
    
    Args:
        preferred_time: User's preferred pickup time
        buffer_before_min: Minutes before preferred_time user can accept pickup
        buffer_after_min: Minutes after preferred_time user can accept pickup
    
    Returns:
        Tuple of (start_time, end_time) representing the acceptable window
    """
    start = preferred_time - timedelta(minutes=buffer_before_min)
    end = preferred_time + timedelta(minutes=buffer_after_min)
    return (start, end)


def time_windows_overlap(
    window1: Tuple[datetime, datetime],
    window2: Tuple[datetime, datetime]
) -> bool:
    """
    Check if two time windows overlap.
    
    Args:
        window1: First time window (start, end)
        window2: Second time window (start, end)
    
    Returns:
        True if windows overlap, False otherwise
    """
    start1, end1 = window1
    start2, end2 = window2
    
    # Windows overlap if one starts before the other ends
    return start1 <= end2 and start2 <= end1
