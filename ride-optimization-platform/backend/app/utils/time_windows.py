"""
Time window computation utilities.
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
        buffer_before_min: Minutes user is willing to depart before preferred time
        buffer_after_min: Minutes user is willing to depart after preferred time
        
    Returns:
        Tuple of (start_time, end_time) representing the acceptable window
    """
    start_time = preferred_time - timedelta(minutes=buffer_before_min)
    end_time = preferred_time + timedelta(minutes=buffer_after_min)
    return (start_time, end_time)


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


def compute_overlap_window(
    window1: Tuple[datetime, datetime],
    window2: Tuple[datetime, datetime]
) -> Tuple[datetime, datetime]:
    """
    Compute the overlapping portion of two time windows.
    
    Args:
        window1: First time window (start, end)
        window2: Second time window (start, end)
        
    Returns:
        Tuple of (start, end) for the overlap. Returns None if no overlap.
    """
    if not time_windows_overlap(window1, window2):
        return None
    
    start1, end1 = window1
    start2, end2 = window2
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    return (overlap_start, overlap_end)
