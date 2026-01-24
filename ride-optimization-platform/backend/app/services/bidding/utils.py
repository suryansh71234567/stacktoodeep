"""
Bidding orchestration utilities.

Helper functions for:
- Coupon code generation (deterministic)
- Timestamp parsing
"""
import hashlib
from datetime import datetime
from typing import Union


def generate_coupon_code(bundle_id: str, company_id: str) -> str:
    """
    Generate a deterministic coupon code from bundle and company IDs.
    
    Uses SHA256 hash to ensure:
    - Determinism: Same inputs always produce same output
    - Uniqueness: Different bundles/companies produce different codes
    - No randomness: Auditable and reproducible
    
    Args:
        bundle_id: Unique bundle identifier
        company_id: Winning company identifier
        
    Returns:
        Coupon code in format "RIDE-XXXXXXXX" (8 hex chars)
    """
    # Create deterministic hash from both IDs
    combined = f"{bundle_id}:{company_id}"
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    # Take first 8 characters for readability
    short_hash = hash_bytes[:8].upper()
    
    return f"RIDE-{short_hash}"


def parse_iso_datetime(dt_input: Union[str, datetime]) -> datetime:
    """
    Parse ISO format datetime string or pass through datetime object.
    
    Args:
        dt_input: ISO datetime string or datetime object
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If string format is invalid
    """
    if isinstance(dt_input, datetime):
        return dt_input
    
    # Handle ISO format with or without timezone
    try:
        # Try standard ISO format first
        return datetime.fromisoformat(dt_input.replace('Z', '+00:00'))
    except ValueError:
        # Fallback for various formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                return datetime.strptime(dt_input, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse datetime: {dt_input}")


def get_earliest_datetime(datetimes: list) -> datetime:
    """
    Get the earliest datetime from a list.
    
    Args:
        datetimes: List of datetime objects or ISO strings
        
    Returns:
        Earliest datetime
        
    Raises:
        ValueError: If list is empty
    """
    if not datetimes:
        raise ValueError("Cannot get earliest from empty list")
    
    parsed = [parse_iso_datetime(dt) for dt in datetimes]
    return min(parsed)
