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
"""Unit tests for A2UI utilities and callback formatting in app/a2ui_utils.py."""

import json
from google.genai import types
from google.adk.models.llm_response import LlmResponse

from app.a2ui_utils import (
    _extract_a2ui_messages,
    _auto_synthesize_begin_rendering,
    _sanitize_image_components,
    _surface_is_renderable,
    a2ui_callback,
)


def test_extract_a2ui_messages():
    """Test extracting A2UI messages from raw JSON array text."""
    sample_text = """
    [
      {"surfaceUpdate": {"surfaceId": "main", "components": [{"id": "card_1", "component": {"Card": {"child": "text_1"}}}]}}
    ]
    """
    messages = _extract_a2ui_messages(sample_text)
    assert len(messages) == 1
    assert "surfaceUpdate" in messages[0]


def test_auto_synthesize_begin_rendering():
    """Test automatic generation of beginRendering when missing."""
    messages = [
        {
            "surfaceUpdate": {
                "surfaceId": "surface_1",
                "components": [
                    {"id": "card_root", "component": {"Card": {"child": "col_1"}}},
                    {"id": "col_1", "component": {"Column": {"children": {"explicitList": []}}}},
                ],
            }
        }
    ]
    synthesized = _auto_synthesize_begin_rendering(messages)
    assert len(synthesized) == 2
    assert "beginRendering" in synthesized[0]
    assert synthesized[0]["beginRendering"]["root"] == "card_root"
    assert synthesized[0]["beginRendering"]["surfaceId"] == "surface_1"


def test_sanitize_image_components():
    """Test sanitizing non-http Image URLs to text notes."""
    messages = [
        {
            "surfaceUpdate": {
                "surfaceId": "s1",
                "components": [
                    {
                        "id": "img_local",
                        "component": {"Image": {"url": {"literalString": "local_file.png"}}},
                    },
                    {
                        "id": "img_remote",
                        "component": {"Image": {"url": {"literalString": "https://storage.googleapis.com/bucket/img.jpg"}}},
                    },
                ],
            }
        }
    ]
    _sanitize_image_components(messages)
    components = messages[0]["surfaceUpdate"]["components"]
    # img_local should be converted to Text
    assert "Text" in components[0]["component"]
    # img_remote should remain Image
    assert "Image" in components[1]["component"]


def test_surface_is_renderable():
    """Test validating renderable surface trees."""
    valid_messages = [
        {"beginRendering": {"root": "card_root", "surfaceId": "s1"}},
        {
            "surfaceUpdate": {
                "surfaceId": "s1",
                "components": [
                    {"id": "card_root", "component": {"Card": {"child": "text_1"}}},
                    {"id": "text_1", "component": {"Text": {"text": {"literalString": "Hello"}}}},
                ],
            }
        },
    ]
    assert _surface_is_renderable(valid_messages) is True


def test_a2ui_callback_transformation():
    """Test full a2ui_callback transformation on LlmResponse."""
    raw_json = json.dumps(
        [
            {
                "surfaceUpdate": {
                    "surfaceId": "test_surf",
                    "components": [
                        {"id": "c_root", "component": {"Card": {"child": "t_root"}}},
                        {"id": "t_root", "component": {"Text": {"text": {"literalString": "Test Card"}}}},
                    ],
                }
            }
        ]
    )
    llm_resp = LlmResponse(content=types.Content(role="model", parts=[types.Part(text=raw_json)]))
    result = a2ui_callback(None, llm_resp)

    assert result is not None
    assert result.custom_metadata == {"a2a:response": "true"}
    assert len(result.content.parts) == 2
    # Verify inline_data Blob containing <a2a_datapart_json>
    blob_0 = result.content.parts[0].inline_data.data.decode("utf-8")
    assert "<a2a_datapart_json>" in blob_0
    assert "beginRendering" in blob_0
