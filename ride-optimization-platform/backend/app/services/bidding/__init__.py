"""
Bidding Orchestration Module

This module controls the bidding lifecycle between:
- Optimization backend (already done)
- Blockchain contracts (already deployed)
- AI bidding agents (external)

Components:
- D5: Pre-Bidding Data Builder
- D6: Bidding Lifecycle Controller
- D7: Post-Bidding Data Distributor
"""

# Types
from app.services.bidding.types import (
    Location,
    PreBiddingPayload,
    WinningBid,
    CompanyPayload,
    UserPayload,
)

# Utils
from app.services.bidding.utils import (
    generate_coupon_code,
    parse_iso_datetime,
    get_earliest_datetime,
)

# D5: Pre-Bidding Data Builder
from app.services.bidding.pre_bidding_builder import (
    build_pre_bidding_payload,
)

# D6: Bidding Lifecycle Controller
from app.services.bidding.lifecycle_controller import (
    BiddingPhase,
    start_bidding,
    transition_to_reveal,
    end_bidding,
    select_winner,
    get_bidding_state,
    set_blockchain_adapter,
    reset_state,
)

# D7: Post-Bidding Data Distributor
from app.services.bidding.post_bidding_distributor import (
    build_company_payload,
    build_user_payload,
    distribute_post_bidding_data,
    set_notification_services,
)


__all__ = [
    # Types
    "Location",
    "PreBiddingPayload",
    "WinningBid",
    "CompanyPayload",
    "UserPayload",
    # Utils
    "generate_coupon_code",
    "parse_iso_datetime",
    "get_earliest_datetime",
    # D5
    "build_pre_bidding_payload",
    # D6
    "BiddingPhase",
    "start_bidding",
    "transition_to_reveal",
    "end_bidding",
    "select_winner",
    "get_bidding_state",
    "set_blockchain_adapter",
    "reset_state",
    # D7
    "build_company_payload",
    "build_user_payload",
    "distribute_post_bidding_data",
    "set_notification_services",
]
