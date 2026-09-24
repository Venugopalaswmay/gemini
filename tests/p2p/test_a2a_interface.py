# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Peer-to-Peer (P2P / A2A) protocol interface tests."""

import uuid
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    TextPart,
)

from app.fast_api_app import app


def test_agent_card_schema():
    """Verify that .well-known/agent-card.json returns valid A2A agent metadata."""
    with TestClient(app) as client:
        response = client.get("/a2a/app/.well-known/agent-card.json")
        assert response.status_code == 200
        card = response.json()
        assert "name" in card
        assert "description" in card
        assert "capabilities" in card
        assert "skills" in card


def test_a2a_rpc_endpoint_structure():
    """Test A2A JSON-RPC interface request parsing and response headers."""
    message = Message(
        message_id=f"msg-p2p-{uuid.uuid4()}",
        role=Role.user,
        parts=[Part(root=TextPart(text="Hello P2P"))],
    )
    request_data = SendStreamingMessageRequest(
        id="p2p-req-001",
        params=MessageSendParams(message=message),
    ).model_dump(mode="json", exclude_none=True)

    with TestClient(app) as client:
        # Mock runner.run on app.state
        mock_runner = MagicMock()

        async def async_gen(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.content.parts = [MagicMock(text="Hello back from agent")]
            mock_event.actions.state_delta = {}
            mock_event.actions.artifact_delta = {}
            yield mock_event

        mock_runner.run.side_effect = async_gen
        app.state.runner = mock_runner

        response = client.post(
            "/a2a/app/",
            json=request_data,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
