"""
Bidding orchestration type definitions.

Defines typed structures for the bidding lifecycle:
- PreBiddingPayload: Data visible to companies before bidding
- WinningBid: Selected bid result
- CompanyPayload: Data sent to winning company
- UserPayload: Data sent to each user
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class Location(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class PreBiddingPayload(BaseModel):
    """
    Minimal information visible to companies BEFORE bidding.
    
    Hides sensitive user details while providing enough
    information for companies to price the ride.
    """
    bundle_id: str = Field(..., description="Unique bundle identifier")
    time: datetime = Field(..., description="Earliest pickup time")
    duration: float = Field(..., ge=0, description="Total route duration in minutes")
    distance: float = Field(..., ge=0, description="Total route distance in km")
    max_bidding_price: float = Field(..., ge=0, description="Maximum allowed bid price")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bundle_id": "550e8400-e29b-41d4-a716-446655440000",
                "time": "2026-01-24T09:00:00",
                "duration": 31.0,
                "distance": 15.5,
                "max_bidding_price": 180.0
            }
        }
    )


class WinningBid(BaseModel):
    """
    Result of bid selection.
    
    Contains the winning company and their bid value.
    """
    company_id: str = Field(..., description="Winning company identifier")
    bid_value: float = Field(..., ge=0, description="Winning bid amount")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company_id": "company_001",
                "bid_value": 165.0
            }
        }
    )


class CompanyPayload(BaseModel):
    """
    Data sent to the WINNING company after bidding ends.
    
    Contains full route details and user identifiers needed
    to fulfill the ride bundle.
    """
    exact_route: str = Field(..., description="Full route representation")
    pickup_points: List[Location] = Field(..., description="All pickup coordinates")
    drop_points: List[Location] = Field(..., description="All drop-off coordinates")
    user_ids: List[str] = Field(..., description="User identifiers in bundle")
    coupon_code: str = Field(..., description="Auto-generated coupon code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exact_route": "pickup_user1->pickup_user2->drop_user1->drop_user2",
                "pickup_points": [{"lat": 28.61, "lng": 77.20}],
                "drop_points": [{"lat": 28.53, "lng": 77.39}],
                "user_ids": ["user_001"],
                "coupon_code": "RIDE-A1B2C3D4"
            }
        }
    )


class UserPayload(BaseModel):
    """
    Data sent to EACH USER after bidding ends.
    
    Contains only the information relevant to their specific ride.
    """
    coupon_code: str = Field(..., description="Coupon code to use for ride")
    pickup_time: datetime = Field(..., description="Scheduled pickup time")
    pickup_location: Location = Field(..., description="Pickup coordinates")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "coupon_code": "RIDE-A1B2C3D4",
                "pickup_time": "2026-01-24T09:00:00",
                "pickup_location": {"lat": 28.61, "lng": 77.20}
            }
        }
    )
