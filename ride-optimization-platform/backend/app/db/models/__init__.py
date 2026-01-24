"""
Database Models Package.

Import all models here for Alembic to discover them.
"""
from app.db.models.ride import RideDB, RideStatus

__all__ = ["RideDB", "RideStatus"]
