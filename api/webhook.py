import os
from datetime import datetime, timezone

# RevenueCat event types that indicate an active subscription
_ACTIVE_EVENTS = {
    "INITIAL_PURCHASE",
    "RENEWAL",
    "UNCANCELLATION",
    "SUBSCRIPTION_EXTENDED",
    "TEMPORARY_ENTITLEMENT_GRANT",
}

# Event types that indicate a subscription is no longer active
_INACTIVE_EVENTS = {
    "CANCELLATION",
    "EXPIRATION",
    "BILLING_ISSUE",
    "SUBSCRIBER_ALIAS",
}


def verify_webhook_secret(authorization: str | None) -> bool:
    secret = os.environ.get("REVENUECAT_WEBHOOK_SECRET", "")
    if not secret:
        return True  # no secret configured — skip verification in dev
    return authorization == secret


def handle_event(db, event: dict) -> None:
    event_type = event.get("type")
    uid = event.get("app_user_id")
    if not uid:
        return

    ref = db.collection("subscribers").document(uid)

    if event_type in _ACTIVE_EVENTS:
        ref.set({
            "is_subscriber": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
        })
    elif event_type in _INACTIVE_EVENTS:
        ref.set({
            "is_subscriber": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
        })
