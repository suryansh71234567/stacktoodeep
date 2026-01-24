"""
SQLAlchemy Base Classes and Mixins.

This module provides the foundational components for all database models:
- Declarative base class
- UUID primary key mixin
- Timestamp mixin for created_at/updated_at tracking
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """
    Declarative base class for all SQLAlchemy models.
    
    All models should inherit from this class to be properly
    registered with SQLAlchemy's metadata.
    """
    pass


class UUIDMixin:
    """
    Mixin that provides a UUID primary key.
    
    Uses PostgreSQL's native UUID type for efficient storage
    and indexing. UUIDs are generated client-side with uuid4.
    """
    
    @declared_attr
    def id(cls):
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
            doc="Unique identifier (UUID v4)"
        )


class TimestampMixin:
    """
    Mixin that provides automatic timestamp tracking.
    
    - created_at: Set automatically when record is created
    - updated_at: Updated automatically on every modification
    
    Uses PostgreSQL server time for consistency across distributed systems.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            default=datetime.utcnow,
            server_default=func.now(),
            nullable=False,
            doc="Timestamp when record was created"
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            default=datetime.utcnow,
            server_default=func.now(),
            onupdate=datetime.utcnow,
            nullable=False,
            doc="Timestamp when record was last updated"
        )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Abstract base model combining Base, UUID, and Timestamp mixins.
    
    Use this as the base class for most models:
    
        class RideDB(BaseModel):
            __tablename__ = "rides"
            user_id = Column(String, index=True)
            ...
    """
    
    __abstract__ = True  # This class won't create a table
    
    def __repr__(self) -> str:
        """String representation showing class name and ID."""
        return f"<{self.__class__.__name__}(id={self.id})>"
