"""
D7: Post-Bidding Data Distributor

Distributes DIFFERENT data to:
1) Winning company - full route details
2) End users - only their own ride info

This ensures role-based data access after bidding completes.
"""
from typing import Any, Dict, List

from app.services.bidding.utils import generate_coupon_code, parse_iso_datetime
from app.services.bidding.types import CompanyPayload, UserPayload, Location


# Type aliases for notification services (assumed to exist)
CompanyNotificationService = Any
UserNotificationService = Any

# Placeholder for notification services
# In production, these would be properly injected
_company_notification_service: CompanyNotificationService = None
_user_notification_service: UserNotificationService = None


def set_notification_services(
    company_service: CompanyNotificationService,
    user_service: UserNotificationService
) -> None:
    """
    Set the notification services for data distribution.
    
    Args:
        company_service: Service with send(company_id, payload) method
        user_service: Service with send(user_id, payload) method
    """
    global _company_notification_service, _user_notification_service
    _company_notification_service = company_service
    _user_notification_service = user_service


def build_company_payload(bundle: Dict[str, Any], winner: Dict[str, Any]) -> CompanyPayload:
    """
    Build the payload to send to the winning company.
    
    Includes full route details and user identifiers.
    
    Args:
        bundle: RideBundle dict
        winner: Winner dict with company_id and bid_value
        
    Returns:
        CompanyPayload with route, points, user_ids, coupon
    """
    users = bundle['users']
    
    # Extract pickup points from all users
    pickup_points = []
    for user in users:
        loc = user['pickup_location']
        if isinstance(loc, dict):
            pickup_points.append(Location(lat=loc['lat'], lng=loc['lng']))
        else:
            pickup_points.append(loc)
    
    # Extract drop points from all users
    drop_points = []
    for user in users:
        loc = user['drop_location']
        if isinstance(loc, dict):
            drop_points.append(Location(lat=loc['lat'], lng=loc['lng']))
        else:
            drop_points.append(loc)
    
    # Extract user IDs
    user_ids = [user['user_id'] for user in users]
    
    # Generate deterministic coupon code
    coupon_code = generate_coupon_code(bundle['bundle_id'], winner['company_id'])
    
    return CompanyPayload(
        exact_route=bundle['route'],
        pickup_points=pickup_points,
        drop_points=drop_points,
        user_ids=user_ids,
        coupon_code=coupon_code
    )


def build_user_payload(
    user: Dict[str, Any], 
    coupon_code: str
) -> UserPayload:
    """
    Build the payload to send to a specific user.
    
    Includes only their own ride information.
    
    Args:
        user: User dict from bundle.users
        coupon_code: Shared coupon code for this bundle
        
    Returns:
        UserPayload with coupon, pickup_time, pickup_location
    """
    pickup_loc = user['pickup_location']
    if isinstance(pickup_loc, dict):
        pickup_location = Location(lat=pickup_loc['lat'], lng=pickup_loc['lng'])
    else:
        pickup_location = pickup_loc
    
    pickup_time = parse_iso_datetime(user['pickup_time'])
    
    return UserPayload(
        coupon_code=coupon_code,
        pickup_time=pickup_time,
        pickup_location=pickup_location
    )


def distribute_post_bidding_data(
    bundle: Dict[str, Any], 
    winner: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Distribute post-bidding data to winner and users.
    
    Sends different data to:
    - Winning company: Full route, all pickup/drop points, user IDs, coupon
    - Each user: Their coupon, pickup time, pickup location
    
    Args:
        bundle: RideBundle dict with the following structure:
            {
                "bundle_id": str,
                "route": str,
                "users": [{"user_id", "pickup_location", "pickup_time", 
                          "drop_location", "drop_time"}],
                ...
            }
        winner: Winner dict:
            {
                "company_id": str,
                "bid_value": float
            }
            
    Returns:
        Distribution result dict:
            {
                "company_payload": CompanyPayload,
                "user_payloads": List[UserPayload],
                "notifications_sent": bool
            }
            
    Note:
        Assumes company_notification_service.send() and 
        user_notification_service.send() exist.
    """
    # Build company payload
    company_payload = build_company_payload(bundle, winner)
    
    # Generate coupon code (same for all users in bundle)
    coupon_code = generate_coupon_code(bundle['bundle_id'], winner['company_id'])
    
    # Build user payloads
    user_payloads: List[UserPayload] = []
    for user in bundle['users']:
        user_payload = build_user_payload(user, coupon_code)
        user_payloads.append(user_payload)
    
    # Send notifications if services are configured
    notifications_sent = False
    
    if _company_notification_service is not None:
        _company_notification_service.send(
            winner['company_id'], 
            company_payload.model_dump()
        )
        notifications_sent = True
    
    if _user_notification_service is not None:
        for user, payload in zip(bundle['users'], user_payloads):
            _user_notification_service.send(
                user['user_id'],
                payload.model_dump()
            )
        notifications_sent = True
    
    return {
        "company_payload": company_payload,
        "user_payloads": user_payloads,
        "notifications_sent": notifications_sent
    }
