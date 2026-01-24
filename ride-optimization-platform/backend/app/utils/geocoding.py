"""
Geocoding Service using Nominatim (OpenStreetMap).

This module provides geocoding utilities to convert between:
- Addresses → Coordinates (geocode)
- Coordinates → Addresses (reverse_geocode)

Uses Nominatim's free API with proper rate limiting (1 req/sec)
as required by their usage policy.

Why this exists:
- Frontend sends human-readable addresses
- Optimization engine needs lat/lng coordinates
- We need to convert between them reliably
"""
import asyncio
import hashlib
import json
from typing import List, Optional

import httpx

from app.models.ride import Location
from app.core.config import settings


# =============================================================================
# Configuration
# =============================================================================

# Nominatim API base URL (OpenStreetMap's free geocoding service)
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"

# User-Agent header (required by Nominatim - identifies your application)
# Using a descriptive name helps Nominatim operators contact you if needed
USER_AGENT = "RideOptimizationPlatform/1.0 (https://github.com/suryansh71234567/stacktoodeep)"

# Request timeout in seconds
TIMEOUT_SECONDS = 10

# Rate limiting: Nominatim requires max 1 request per second
RATE_LIMIT_SECONDS = 1.0

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Simple in-memory cache (use Redis in production for distributed systems)
_geocode_cache: dict = {}


# =============================================================================
# HTTP Client
# =============================================================================

def _get_http_client() -> httpx.AsyncClient:
    """
    Create an async HTTP client with proper headers and timeout.
    
    Why async: Non-blocking I/O allows handling multiple requests
    concurrently without blocking the event loop.
    """
    return httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(TIMEOUT_SECONDS),
    )


def _get_cache_key(prefix: str, value: str) -> str:
    """Generate a cache key from prefix and value."""
    return f"{prefix}:{hashlib.md5(value.encode()).hexdigest()}"


# =============================================================================
# Core Geocoding Functions
# =============================================================================

async def geocode(address: str) -> Location:
    """
    Convert a human-readable address to geographic coordinates.
    
    Why this exists:
    - Users input addresses like "Connaught Place, Delhi"
    - Optimization engine needs coordinates (28.6139, 77.2090)
    - This bridges that gap
    
    Args:
        address: Human-readable address string
        
    Returns:
        Location object with latitude, longitude, and address
        
    Raises:
        ValueError: If address cannot be found
        httpx.HTTPError: If API request fails after retries
        
    Example:
        >>> location = await geocode("Connaught Place, New Delhi")
        >>> print(location.latitude, location.longitude)
        28.6304, 77.2177
    """
    if not address or not address.strip():
        raise ValueError("Address cannot be empty")
    
    address = address.strip()
    
    # Check cache first
    cache_key = _get_cache_key("geocode", address)
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    
    # Build request URL
    url = f"{NOMINATIM_BASE_URL}/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    
    # Make request with retry logic
    result = await _make_request_with_retry(url, params)
    
    if not result or len(result) == 0:
        raise ValueError(f"Address not found: {address}")
    
    # Parse response
    data = result[0]
    location = Location(
        latitude=float(data["lat"]),
        longitude=float(data["lon"]),
        address=data.get("display_name", address),
    )
    
    # Cache the result
    _geocode_cache[cache_key] = location
    
    return location


async def reverse_geocode(lat: float, lon: float) -> str:
    """
    Convert geographic coordinates to a human-readable address.
    
    Why this exists:
    - Sometimes we have coordinates (from GPS, maps)
    - Need to display readable addresses to users
    - Useful for ride confirmation screens
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        
    Returns:
        Formatted address string
        
    Raises:
        ValueError: If coordinates are invalid or location not found
        httpx.HTTPError: If API request fails after retries
        
    Example:
        >>> address = await reverse_geocode(28.6139, 77.2090)
        >>> print(address)
        "Connaught Place, New Delhi, Delhi, 110001, India"
    """
    # Validate coordinates
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90.")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180.")
    
    # Check cache
    cache_key = _get_cache_key("reverse", f"{lat},{lon}")
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    
    # Build request URL
    url = f"{NOMINATIM_BASE_URL}/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    
    # Make request with retry logic
    result = await _make_request_with_retry(url, params)
    
    if not result or "error" in result:
        raise ValueError(f"Location not found for coordinates: ({lat}, {lon})")
    
    address = result.get("display_name", f"{lat}, {lon}")
    
    # Cache the result
    _geocode_cache[cache_key] = address
    
    return address


async def batch_geocode(addresses: List[str]) -> List[Optional[Location]]:
    """
    Geocode multiple addresses while respecting rate limits.
    
    Why this exists:
    - When creating multiple ride requests, we need to geocode all addresses
    - Must respect Nominatim's 1 request/second rate limit
    - Handles errors gracefully without failing the entire batch
    
    Args:
        addresses: List of address strings to geocode
        
    Returns:
        List of Location objects (None for failed geocodes)
        Results are in the same order as input addresses
        
    Example:
        >>> locations = await batch_geocode([
        ...     "Connaught Place, Delhi",
        ...     "Sector 18, Noida",
        ...     "Invalid Address XYZ"
        ... ])
        >>> # locations[0] and [1] are Location objects
        >>> # locations[2] is None (failed)
    """
    if not addresses:
        return []
    
    results: List[Optional[Location]] = []
    
    for i, address in enumerate(addresses):
        try:
            location = await geocode(address)
            results.append(location)
        except (ValueError, httpx.HTTPError) as e:
            # Log the error but don't fail the batch
            print(f"Failed to geocode address '{address}': {e}")
            results.append(None)
        
        # Rate limiting: wait 1 second between requests
        # Skip wait after the last request
        if i < len(addresses) - 1:
            await asyncio.sleep(RATE_LIMIT_SECONDS)
    
    return results


# =============================================================================
# Helper Functions
# =============================================================================

async def _make_request_with_retry(
    url: str,
    params: dict,
    max_retries: int = MAX_RETRIES,
) -> Optional[dict]:
    """
    Make HTTP request with exponential backoff retry logic.
    
    Why retry logic:
    - Network can be unreliable
    - Nominatim might be temporarily busy
    - Exponential backoff prevents hammering the server
    
    Args:
        url: API endpoint URL
        params: Query parameters
        max_retries: Maximum number of retry attempts
        
    Returns:
        JSON response as dict, or None if all retries fail
        
    Raises:
        httpx.HTTPError: If request fails after all retries
    """
    backoff = INITIAL_BACKOFF_SECONDS
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            async with _get_http_client() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            last_exception = e
            # Don't retry on 4xx client errors (except 429 rate limit)
            if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                raise
            
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exception = e
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff)
            backoff *= 2  # Double the wait time for next retry
    
    # All retries exhausted
    if last_exception:
        raise last_exception
    
    return None


def clear_cache() -> None:
    """
    Clear the geocoding cache.
    
    Useful for testing or when you need fresh results.
    """
    global _geocode_cache
    _geocode_cache = {}


def get_cache_stats() -> dict:
    """
    Get statistics about the geocoding cache.
    
    Returns:
        Dict with cache size and keys
    """
    return {
        "size": len(_geocode_cache),
        "keys": list(_geocode_cache.keys())[:10],  # First 10 keys only
    }
