"""Integration and unit tests for Redis Pub/Sub WebSocket streaming and buyer alerts.

Acceptance criteria for Issue #17:
- WebSocket connection authenticates JWT token and verifies household membership.
- Mutations via REST or /sync publish real-time events to connected household clients.
- FCM service gracefully handles missing credentials in local/CI environments.
"""

from __future__ import annotations

import uuid
from typing import Dict, Tuple
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.main import app
from src.services.notification_service import (
    format_buyer_topic,
    notify_buyers_item_depleted,
)
from src.services.pubsub_service import (
    EVENT_CONNECTED,
    EVENT_ITEM_DELETED,
    EVENT_ITEM_UPDATED,
)


@pytest.fixture
def client() -> TestClient:
    """Fixture providing TestClient instance."""
    return TestClient(app)


def _create_authenticated_user_and_home(
    client: TestClient,
    username: str,
    email: str,
    home_name: str,
) -> Tuple[str, str, Dict[str, str]]:
    """Helper to register user, create home, and return auth details."""
    uid = uuid.uuid4().hex[:8]
    unique_user = f"{username}_{uid}"
    unique_email = f"{uid}_{email}"
    password = "SecurePassword123!"

    # 1. Register unique user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": unique_user,
            "email": unique_email,
            "password": password,
        },
    )
    assert reg_res.status_code == 201

    # 2. Login
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Household
    home_res = client.post(
        "/api/v1/homes",
        json={"name": f"{home_name} {uid}"},
        headers=headers,
    )
    assert home_res.status_code == 201
    home_id = home_res.json()["id"]

    return token, home_id, headers


def test_websocket_authentication_and_membership_guards(client: TestClient) -> None:
    """Verify WebSocket connection enforces JWT auth and household membership."""
    token, home_id, _ = _create_authenticated_user_and_home(
        client, "ws_guard_user", "ws_guard@example.com", "Guard Villa"
    )

    # 1. Reject unauthenticated WebSocket connection
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/homes/{home_id}/ws"):
            pass
    assert exc_info.value.code == 1008

    # 2. Reject invalid token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/homes/{home_id}/ws?token=invalid_jwt"):
            pass
    assert exc_info.value.code == 1008

    # 3. Reject user who is not a member of the home
    other_token, _, _ = _create_authenticated_user_and_home(
        client, "stranger_user", "stranger@example.com", "Stranger Home"
    )
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            f"/api/v1/homes/{home_id}/ws?token={other_token}"
        ):
            pass
    assert exc_info.value.code == 1008

    # 4. Accept authorized household member
    with client.websocket_connect(f"/api/v1/homes/{home_id}/ws?token={token}") as ws:
        ack = ws.receive_json()
        assert ack["event"] == EVENT_CONNECTED
        assert ack["home_id"] == home_id
        assert ack["role"] == "buyer"


def test_realtime_pantry_mutations_and_broadcast(client: TestClient) -> None:
    """Verify REST pantry mutations stream real-time events to WebSocket clients."""
    token, home_id, headers = _create_authenticated_user_and_home(
        client, "stream_user", "stream@example.com", "Stream Villa"
    )

    with client.websocket_connect(f"/api/v1/homes/{home_id}/ws?token={token}") as ws:
        # Acknowledge connection
        ack = ws.receive_json()
        assert ack["event"] == EVENT_CONNECTED

        # 1. CREATE item via REST -> should broadcast ITEM_UPDATED
        create_res = client.post(
            f"/api/v1/homes/{home_id}/pantry",
            headers=headers,
            json={
                "custom_name": "Artisanal Sourdough",
                "quantity": 1.0,
                "unit_type": "loaf",
                "low_stock_threshold": 1.0,
                "status": "ok",
            },
        )
        assert create_res.status_code == 201
        created_item = create_res.json()
        item_id = created_item["id"]

        create_event = ws.receive_json()
        assert create_event["event"] == EVENT_ITEM_UPDATED
        assert create_event["home_id"] == home_id
        assert create_event["data"]["id"] == item_id
        assert create_event["data"]["custom_name"] == "Artisanal Sourdough"
        assert create_event["data"]["status"] == "ok"

        # 2. UPDATE item via REST -> should broadcast ITEM_UPDATED
        patch_res = client.patch(
            f"/api/v1/homes/{home_id}/pantry/{item_id}",
            headers=headers,
            json={
                "status": "low",
                "quantity": 0.5,
            },
        )
        assert patch_res.status_code == 200

        update_event = ws.receive_json()
        assert update_event["event"] == EVENT_ITEM_UPDATED
        assert update_event["data"]["id"] == item_id
        assert update_event["data"]["status"] == "low"

        # 3. DELETE item via REST -> should broadcast ITEM_DELETED
        del_res = client.delete(
            f"/api/v1/homes/{home_id}/pantry/{item_id}",
            headers=headers,
        )
        assert del_res.status_code == 200

        del_event = ws.receive_json()
        assert del_event["event"] == EVENT_ITEM_DELETED
        assert del_event["data"]["id"] == item_id
        assert del_event["data"]["is_deleted"] is True


def test_delta_sync_batch_publishes_websocket_events(client: TestClient) -> None:
    """Verify offline delta-sync batch publishes events for applied server deltas."""
    token, home_id, headers = _create_authenticated_user_and_home(
        client, "sync_stream_user", "sync_stream@example.com", "Sync Stream Lodge"
    )

    with client.websocket_connect(f"/api/v1/homes/{home_id}/ws?token={token}") as ws:
        ack = ws.receive_json()
        assert ack["event"] == EVENT_CONNECTED

        # Submit offline delta sync with a new item mutation
        sync_item_id = str(uuid.uuid4())
        sync_res = client.post(
            f"/api/v1/homes/{home_id}/pantry/sync",
            headers=headers,
            json={
                "last_synced_at": None,
                "mutations": [
                    {
                        "id": sync_item_id,
                        "custom_name": "Greek Yogurt",
                        "quantity": 2.0,
                        "unit_type": "tub",
                        "low_stock_threshold": 1.0,
                        "status": "ok",
                        "updated_at": "2026-11-19T10:00:00Z",
                        "is_deleted": False,
                    }
                ],
            },
        )
        assert sync_res.status_code == 200
        assert sync_res.json()["applied_mutations_count"] == 1

        sync_event = ws.receive_json()
        assert sync_event["event"] == EVENT_ITEM_UPDATED
        assert sync_event["data"]["id"] == sync_item_id
        assert sync_event["data"]["custom_name"] == "Greek Yogurt"


def test_fcm_notification_service_graceful_missing_credentials() -> None:
    """Verify FCM service handles missing credentials without failing."""
    random_home_id = uuid.uuid4()
    topic = format_buyer_topic(random_home_id)
    assert f"home_{str(random_home_id).replace('-', '_')}_buyers" == topic

    # 1. Ignored status test ('ok' status does not trigger push)
    res_ok = notify_buyers_item_depleted(
        home_id=random_home_id,
        item_name="Full Cream Milk",
        status="ok",
    )
    assert res_ok["status"] == "ignored"

    # 2. Low staple status test without Firebase credentials (simulation fallback)
    res_low = notify_buyers_item_depleted(
        home_id=random_home_id,
        item_name="Brown Rice",
        status="low",
        quantity="0.25",
        buyer_emails=["buyer@example.com"],
    )
    assert res_low["status"] == "simulated"
    assert res_low["topic"] == topic
    assert "buyer@example.com" in res_low["recipients"]
    assert "LOW" in res_low["title"]
    assert "Brown Rice" in res_low["body"]

    # 3. Finished staple status test
    res_fin = notify_buyers_item_depleted(
        home_id=random_home_id,
        item_name="Canola Oil",
        status="finished",
        buyer_emails=["chef@example.com"],
    )
    assert res_fin["status"] == "simulated"
    assert "FINISHED" in res_fin["title"]


def test_fcm_notification_dispatch_with_mocked_messaging() -> None:
    """Verify FCM service constructs and dispatches messaging payload when active."""
    test_home_id = uuid.uuid4()
    mock_app = MagicMock()

    with patch(
        "src.services.notification_service.get_firebase_app", return_value=mock_app
    ):
        with patch(
            "firebase_admin.messaging.send",
            return_value="projects/test/messages/msg-12345",
        ) as mock_send:
            res = notify_buyers_item_depleted(
                home_id=test_home_id,
                item_name="Organic Eggs",
                status="low",
                quantity="2",
                buyer_emails=["parent@example.com"],
            )

            assert res["status"] == "sent"
            assert res["message_id"] == "projects/test/messages/msg-12345"
            assert mock_send.called
            sent_msg = mock_send.call_args[0][0]
            assert sent_msg.notification.title == "Pantry Alert: Organic Eggs is LOW!"
            assert "Organic Eggs" in sent_msg.notification.body
            assert sent_msg.topic == format_buyer_topic(test_home_id)
            assert sent_msg.data["status"] == "low"
