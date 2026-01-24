"""
OSRM Routing Service.

This module provides routing utilities using OSRM (Open Source Routing Machine)
to calculate actual road distances and durations (not straight-line).

IMPORTANT: OSRM uses lon,lat format (NOT lat,lon like most other services).
This module handles the conversion internally.

Why OSRM:
- Free and open-source
- Uses actual road network data
- Fast response times
- Provides polyline encoding for route visualization
"""
import logging
from typing import List, Tuple, Optional

import httpx

from app.models.ride import Location
from app.core.config import settings


# =============================================================================
# Configuration
# =============================================================================

# OSRM public demo server (replace with self-hosted for production)
OSRM_BASE_URL = getattr(settings, 'OSRM_BASE_URL', "http://router.project-osrm.org")

# Request timeout in seconds (OSRM can be slow for complex routes)
TIMEOUT_SECONDS = 30

# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class RoutingError(Exception):
    """Base exception for routing errors."""
    pass


class OSRMError(RoutingError):
    """Error from OSRM API."""
    def __init__(self, message: str, code: str = None):
        self.code = code
        super().__init__(message)


class InvalidCoordinatesError(RoutingError):
    """Invalid coordinates provided."""
    pass


class NoRouteFoundError(RoutingError):
    """No route could be found between the points."""
    pass


# =============================================================================
# RoutingService Class
# =============================================================================

class RoutingService:
    """
    Async routing service using OSRM API.
    
    Provides methods to calculate road distances, durations, and matrices
    using the Open Source Routing Machine.
    
    IMPORTANT: OSRM uses longitude,latitude format (reversed from standard).
    This class handles the conversion internally - you provide Location objects
    with latitude/longitude and it handles the rest.
    
    Example:
        >>> service = RoutingService()
        >>> distance_km, duration_min, polyline = await service.get_route([
        ...     Location(latitude=28.6139, longitude=77.2090),
        ...     Location(latitude=28.5355, longitude=77.3910)
        ... ])
        >>> print(f"Distance: {distance_km} km, Duration: {duration_min} min")
    """
    
    def __init__(self, base_url: str = None, timeout: int = TIMEOUT_SECONDS):
        """
        Initialize the routing service.
        
        Args:
            base_url: OSRM API base URL (defaults to public demo server)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or OSRM_BASE_URL
        self.timeout = timeout
    
    def _get_client(self) -> httpx.AsyncClient:
        """Create an async HTTP client with proper timeout."""
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"Accept": "application/json"},
        )
    
    def _validate_location(self, location: Location) -> None:
        """
        Validate that a location has valid coordinates.
        
        Args:
            location: Location to validate
            
        Raises:
            InvalidCoordinatesError: If coordinates are out of range
        """
        if not (-90 <= location.latitude <= 90):
            raise InvalidCoordinatesError(
                f"Invalid latitude: {location.latitude}. Must be between -90 and 90."
            )
        if not (-180 <= location.longitude <= 180):
            raise InvalidCoordinatesError(
                f"Invalid longitude: {location.longitude}. Must be between -180 and 180."
            )
    
    def _format_coordinates(self, locations: List[Location]) -> str:
        """
        Format locations as OSRM coordinate string.
        
        OSRM expects: lon1,lat1;lon2,lat2;...
        NOTE: OSRM uses lon,lat (NOT lat,lon)!
        
        Args:
            locations: List of Location objects
            
        Returns:
            Semicolon-separated coordinate string in OSRM format
        """
        coords = []
        for loc in locations:
            self._validate_location(loc)
            # OSRM format: longitude,latitude (reversed!)
            coords.append(f"{loc.longitude},{loc.latitude}")
        return ";".join(coords)
    
    async def get_route(
        self, 
        locations: List[Location]
    ) -> Tuple[float, float, str]:
        """
        Calculate route through multiple points in order.
        
        Uses OSRM's /route/v1/driving/ endpoint to find the best route
        through the given waypoints in order.
        
        Args:
            locations: List of Location objects to route through (ordered)
                      Minimum 2 locations required.
        
        Returns:
            Tuple of:
            - distance_km (float): Total route distance in kilometers
            - duration_minutes (float): Total travel time in minutes
            - polyline (str): Encoded polyline string for map visualization
            
        Raises:
            InvalidCoordinatesError: If any location has invalid coordinates
            NoRouteFoundError: If no route exists between points
            OSRMError: If OSRM API returns an error
            
        Example:
            >>> service = RoutingService()
            >>> locations = [
            ...     Location(latitude=28.6139, longitude=77.2090),  # Connaught Place
            ...     Location(latitude=28.5355, longitude=77.3910),  # Noida
            ... ]
            >>> distance, duration, polyline = await service.get_route(locations)
            >>> print(f"{distance:.1f} km in {duration:.0f} minutes")
            18.5 km in 42 minutes
        """
        if len(locations) < 2:
            raise ValueError("At least 2 locations required for routing")
        
        # Build OSRM URL
        coords = self._format_coordinates(locations)
        url = f"{self.base_url}/route/v1/driving/{coords}"
        
        params = {
            "overview": "full",       # Get complete route geometry
            "geometries": "polyline", # Encoded polyline format
            "steps": "false",         # Don't need turn-by-turn navigation
        }
        
        logger.debug(f"OSRM request: {url}")
        
        async with self._get_client() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException:
                raise OSRMError("OSRM request timed out")
            except httpx.HTTPError as e:
                raise OSRMError(f"OSRM HTTP error: {e}")
        
        # Check OSRM response status
        if data.get("code") != "Ok":
            code = data.get("code", "Unknown")
            message = data.get("message", "No route found")
            if code == "NoRoute":
                raise NoRouteFoundError(f"No route found between points: {message}")
            raise OSRMError(message, code=code)
        
        # Extract route data
        routes = data.get("routes", [])
        if not routes:
            raise NoRouteFoundError("OSRM returned no routes")
        
        route = routes[0]  # Best route
        
        # Distance in meters -> kilometers
        distance_km = route.get("distance", 0) / 1000.0
        
        # Duration in seconds -> minutes
        duration_minutes = route.get("duration", 0) / 60.0
        
        # Polyline for map visualization
        polyline = route.get("geometry", "")
        
        logger.info(f"Route: {distance_km:.2f} km, {duration_minutes:.1f} min")
        
        return (distance_km, duration_minutes, polyline)
    
    async def get_distance_matrix(
        self,
        sources: List[Location],
        destinations: List[Location]
    ) -> List[List[float]]:
        """
        Get travel time matrix between sources and destinations.
        
        Uses OSRM's /table/v1/driving/ endpoint to efficiently compute
        all pairwise travel times. Essential for optimization algorithms.
        
        Args:
            sources: List of origin Location objects
            destinations: List of destination Location objects
            
        Returns:
            2D list where matrix[i][j] = travel time in minutes
            from sources[i] to destinations[j].
            Returns -1 for pairs with no route.
            
        Raises:
            InvalidCoordinatesError: If any location has invalid coordinates
            OSRMError: If OSRM API returns an error
            
        Example:
            >>> service = RoutingService()
            >>> sources = [Location(latitude=28.6139, longitude=77.2090)]
            >>> destinations = [
            ...     Location(latitude=28.5355, longitude=77.3910),
            ...     Location(latitude=28.4595, longitude=77.0266)
            ... ]
            >>> matrix = await service.get_distance_matrix(sources, destinations)
            >>> print(matrix[0])  # Times from source[0] to each destination
            [42.5, 55.3]
        """
        if not sources or not destinations:
            raise ValueError("Sources and destinations cannot be empty")
        
        # Combine all locations (sources first, then destinations)
        all_locations = sources + destinations
        coords = self._format_coordinates(all_locations)
        
        # Build OSRM URL
        url = f"{self.base_url}/table/v1/driving/{coords}"
        
        # Source indices: 0 to len(sources)-1
        # Destination indices: len(sources) to len(all_locations)-1
        source_indices = ";".join(str(i) for i in range(len(sources)))
        dest_indices = ";".join(str(i) for i in range(len(sources), len(all_locations)))
        
        params = {
            "sources": source_indices,
            "destinations": dest_indices,
            "annotations": "duration",  # Get travel times
        }
        
        logger.debug(f"OSRM table request: {len(sources)}x{len(destinations)} matrix")
        
        async with self._get_client() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException:
                raise OSRMError("OSRM matrix request timed out")
            except httpx.HTTPError as e:
                raise OSRMError(f"OSRM HTTP error: {e}")
        
        # Check response status
        if data.get("code") != "Ok":
            raise OSRMError(
                data.get("message", "Matrix calculation failed"),
                code=data.get("code")
            )
        
        # Extract durations (in seconds) and convert to minutes
        durations = data.get("durations", [])
        
        # Convert seconds to minutes, handle null values
        matrix = []
        for row in durations:
            converted_row = []
            for duration in row:
                if duration is None:
                    converted_row.append(-1)  # No route
                else:
                    converted_row.append(duration / 60.0)  # Convert to minutes
            matrix.append(converted_row)
        
        logger.info(f"Distance matrix: {len(sources)}x{len(destinations)}")
        
        return matrix
    
    async def get_duration(
        self,
        start: Location,
        end: Location
    ) -> float:
        """
        Get travel time between two points.
        
        Simple point-to-point travel time helper. Uses get_route internally.
        
        Args:
            start: Starting location
            end: Ending location
            
        Returns:
            Travel time in minutes
            
        Raises:
            InvalidCoordinatesError: If coordinates are invalid
            NoRouteFoundError: If no route exists
            OSRMError: If OSRM API returns an error
            
        Example:
            >>> service = RoutingService()
            >>> start = Location(latitude=28.6139, longitude=77.2090)
            >>> end = Location(latitude=28.5355, longitude=77.3910)
            >>> duration = await service.get_duration(start, end)
            >>> print(f"Travel time: {duration:.0f} minutes")
            Travel time: 42 minutes
        """
        _, duration_minutes, _ = await self.get_route([start, end])
        return duration_minutes
    
    async def get_distance(
        self,
        start: Location,
        end: Location
    ) -> float:
        """
        Get road distance between two points.
        
        Args:
            start: Starting location
            end: Ending location
            
        Returns:
            Distance in kilometers
        """
        distance_km, _, _ = await self.get_route([start, end])
        return distance_km


# =============================================================================
# Module-level convenience functions
# =============================================================================

# Default service instance
_default_service: Optional[RoutingService] = None


def get_routing_service() -> RoutingService:
    """Get or create the default routing service instance."""
    global _default_service
    if _default_service is None:
        _default_service = RoutingService()
    return _default_service


async def get_route(locations: List[Location]) -> Tuple[float, float, str]:
    """Convenience function using default service."""
    return await get_routing_service().get_route(locations)


async def get_distance_matrix(
    sources: List[Location],
    destinations: List[Location]
) -> List[List[float]]:
    """Convenience function using default service."""
    return await get_routing_service().get_distance_matrix(sources, destinations)


async def get_duration(start: Location, end: Location) -> float:
    """Convenience function using default service."""
    return await get_routing_service().get_duration(start, end)
