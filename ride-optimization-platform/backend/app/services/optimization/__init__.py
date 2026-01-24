"""
Optimization services package.
"""
from app.services.optimization.optimizer import optimize_rides
from app.services.optimization.pooling import pool_rides, are_rides_poolable
from app.services.optimization.solver import solve_cluster
from app.services.optimization.routing import (
    haversine_distance_km,
    estimate_route_distance_and_time
)
from app.services.optimization.utils import compute_pooling_efficiency

__all__ = [
    "optimize_rides",
    "pool_rides",
    "are_rides_poolable",
    "solve_cluster",
    "haversine_distance_km",
    "estimate_route_distance_and_time",
    "compute_pooling_efficiency",
]
