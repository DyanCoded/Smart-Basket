"""Redis Pub/Sub service for real-time household pantry synchronization.

Provides channel broadcasting for household pantry events (ITEM_UPDATED, ITEM_DELETED)
backed by redis.asyncio Pub/Sub (channel: home:{home_id}) with automatic
fallback for offline or test environments.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

import redis
import redis.asyncio as aioredis

from src.core.config import REDIS_URL

logger = logging.getLogger(__name__)

EVENT_ITEM_UPDATED = "ITEM_UPDATED"
EVENT_ITEM_DELETED = "ITEM_DELETED"
EVENT_CONNECTED = "CONNECTED"

# In-memory subscriber registry for resilient fallback when Redis is unreachable
_in_memory_subscribers: Dict[str, Set[asyncio.Queue[str]]] = {}


def get_home_channel(home_id: uuid.UUID | str) -> str:
    """Format the canonical Redis channel name for a household."""
    return f"home:{str(home_id)}"


def register_in_memory_listener(channel: str) -> asyncio.Queue[str]:
    """Register an in-memory queue listener for fallback broadcast."""
    if channel not in _in_memory_subscribers:
        _in_memory_subscribers[channel] = set()
    queue: asyncio.Queue[str] = asyncio.Queue()
    _in_memory_subscribers[channel].add(queue)
    return queue


def unregister_in_memory_listener(channel: str, queue: asyncio.Queue[str]) -> None:
    """Unregister an in-memory queue listener."""
    if channel in _in_memory_subscribers:
        _in_memory_subscribers[channel].discard(queue)
        if not _in_memory_subscribers[channel]:
            del _in_memory_subscribers[channel]


def format_pantry_event(
    home_id: uuid.UUID | str,
    event_type: str,
    data: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build standardized JSON event payload for WebSocket broadcast."""
    ts = timestamp or datetime.now(timezone.utc)
    return {
        "event": event_type,
        "home_id": str(home_id),
        "timestamp": ts.isoformat(),
        "data": data,
    }


def publish_pantry_event(
    home_id: uuid.UUID | str,
    event_type: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Publish a pantry mutation event to Redis and in-memory listeners.

    Args:
        home_id: Household UUID.
        event_type: 'ITEM_UPDATED' or 'ITEM_DELETED'.
        data: Serialized item payload or tombstone.

    Returns:
        The generated event payload dictionary.
    """
    channel = get_home_channel(home_id)
    payload = format_pantry_event(home_id=home_id, event_type=event_type, data=data)
    json_str = json.dumps(payload, default=str)

    redis_published = False
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.publish(channel, json_str)
        client.close()
        redis_published = True
        logger.debug(
            "Published %s to Redis channel %s: %s", event_type, channel, payload
        )
    except Exception as exc:
        logger.warning(
            "Redis sync publish to channel '%s' failed: %s (falling back to in-memory)",
            channel,
            exc,
        )

    # Deliver to in-memory queues (if Redis failed or for active local subscribers)
    if not redis_published and channel in _in_memory_subscribers:
        for q in list(_in_memory_subscribers[channel]):
            try:
                q.put_nowait(json_str)
            except Exception as q_exc:
                logger.debug("Failed delivering to in-memory subscriber: %s", q_exc)

    return payload


async def async_publish_pantry_event(
    home_id: uuid.UUID | str,
    event_type: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Asynchronously publish a pantry mutation event to listeners."""
    channel = get_home_channel(home_id)
    payload = format_pantry_event(home_id=home_id, event_type=event_type, data=data)
    json_str = json.dumps(payload, default=str)

    redis_published = False
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await client.publish(channel, json_str)
        await client.aclose()
        redis_published = True
        logger.debug(
            "Async published %s to Redis channel %s: %s", event_type, channel, payload
        )
    except Exception as exc:
        logger.warning(
            "Redis async publish to channel '%s' failed: %s (using fallback)",
            channel,
            exc,
        )

    if not redis_published and channel in _in_memory_subscribers:
        for q in list(_in_memory_subscribers[channel]):
            try:
                q.put_nowait(json_str)
            except Exception as q_exc:
                logger.debug(
                    "Failed delivering to in-memory async subscriber: %s", q_exc
                )

    return payload
