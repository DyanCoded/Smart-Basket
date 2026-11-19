"""Firebase Cloud Messaging (FCM) push notification service.

Notifies household buyer members when staples run low or finished.
Gracefully handles missing or unconfigured credentials in local and CI environments
by logging simulated alerts without throwing exceptions.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from src.core.config import FCM_ENABLED, FIREBASE_CREDENTIALS_PATH

logger = logging.getLogger(__name__)

_firebase_app: Optional[Any] = None


def get_firebase_app() -> Optional[Any]:
    """Retrieve or initialize the singleton Firebase Admin App instance.

    Returns:
        firebase_admin.App instance if credentials exist, otherwise None.
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if not FCM_ENABLED or not FIREBASE_CREDENTIALS_PATH:
        logger.info(
            "FCM not enabled or credentials path not set. "
            "Push notifications will run in simulation mode."
        )
        return None

    if not os.path.exists(FIREBASE_CREDENTIALS_PATH):
        logger.info(
            "FCM credentials file not found at '%s'. "
            "Push notifications will run in simulation mode.",
            FIREBASE_CREDENTIALS_PATH,
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(
                "Firebase Admin initialized with credentials from %s",
                FIREBASE_CREDENTIALS_PATH,
            )
        else:
            _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except Exception as exc:
        logger.warning(
            "Failed initializing Firebase Admin app: %s. Running in simulation mode.",
            exc,
        )
        return None


def format_buyer_topic(home_id: uuid.UUID | str) -> str:
    """Format the FCM broadcast topic for buyers of a specific household."""
    clean_id = str(home_id).replace("-", "_")
    return f"home_{clean_id}_buyers"


def notify_buyers_item_depleted(
    home_id: uuid.UUID | str,
    item_name: str,
    status: str,
    quantity: Optional[str] = None,
    buyer_emails: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Notify buyer members that a pantry staple has reached low or finished status.

    Args:
        home_id: Household UUID.
        item_name: Name of the depleted product or custom item.
        status: 'low' or 'finished'.
        quantity: Optional remaining quantity string.
        buyer_emails: Optional list of buyer member email addresses.

    Returns:
        Dictionary describing the notification dispatch result.
    """
    if status not in ("low", "finished"):
        return {
            "status": "ignored",
            "reason": f"Status '{status}' does not trigger buyer push alerts",
        }

    topic = format_buyer_topic(home_id)
    title = f"Pantry Alert: {item_name} is {status.upper()}!"
    body = f"'{item_name}' was marked as {status} in your household pantry."
    if quantity:
        body += f" Current quantity: {quantity}."

    payload_data = {
        "home_id": str(home_id),
        "item_name": str(item_name),
        "status": str(status),
    }
    recipients = buyer_emails or []

    app = get_firebase_app()
    if app is not None:
        try:
            from firebase_admin import messaging

            msg = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=payload_data,
                topic=topic,
            )
            message_id = messaging.send(msg)
            logger.info(
                "FCM push notification dispatched: message_id=%s, topic=%s, buyers=%s",
                message_id,
                topic,
                recipients,
            )
            return {
                "status": "sent",
                "message_id": message_id,
                "topic": topic,
                "recipients": recipients,
                "title": title,
                "body": body,
            }
        except Exception as exc:
            logger.warning(
                "FCM messaging.send failed: %s. Falling back to simulation.", exc
            )

    # Simulated notification fallback
    logger.info(
        "FCM Push Alert [SIMULATED]: topic=%s, buyers=%s, title='%s', body='%s'",
        topic,
        recipients or ["all-household-buyers"],
        title,
        body,
    )
    return {
        "status": "simulated",
        "topic": topic,
        "recipients": recipients,
        "title": title,
        "body": body,
    }
