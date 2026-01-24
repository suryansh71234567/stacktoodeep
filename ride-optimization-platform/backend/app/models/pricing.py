"""
Pricing breakdown data models.
"""
from pydantic import BaseModel, Field


class PricingBreakdown(BaseModel):
    """
    Economic breakdown for a ride bundle.
    
    Contains driver profit, user savings, and broker commission
    for use by downstream AI agents and blockchain contracts.
    """
    baseline_driver_profit: float = Field(
        ..., 
        ge=0, 
        description="Driver profit without optimization (distance * 10)"
    )
    optimized_driver_profit: float = Field(
        ..., 
        ge=0, 
        description="Driver profit with pooling efficiency applied"
    )
    total_user_savings: float = Field(
        ..., 
        ge=0, 
        description="Total savings for all users in the bundle"
    )
    broker_commission: float = Field(
        ..., 
        ge=0, 
        description="Platform commission (10% of optimized profit)"
    )
    pooling_efficiency: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Efficiency gain from pooling (0.0 to 1.0)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "baseline_driver_profit": 150.0,
                "optimized_driver_profit": 180.0,
                "total_user_savings": 45.0,
                "broker_commission": 18.0,
                "pooling_efficiency": 0.2
            }
        }
