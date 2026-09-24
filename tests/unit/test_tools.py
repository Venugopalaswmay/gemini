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
"""Unit tests for agent tools and helpers in app/agent.py."""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.agent import (
    get_current_location,
    geocode_address,
    get_live_weather,
    get_vibe_spots,
    add_vibe_spot,
    execute_python_code,
)


def test_get_current_location_success():
    """Test get_current_location when IP API succeeds."""
    fake_response_data = {
        "status": "success",
        "city": "Groningen",
        "regionName": "Groningen",
        "country": "Netherlands",
        "lat": 53.2193,
        "lon": 6.5665,
    }
    
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = get_current_location()
        assert "Groningen" in res
        assert "53.2193" in res


def test_get_current_location_failure():
    """Test get_current_location fallback when URL fetch fails."""
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        res = get_current_location()
        assert "Could not" in res or "fail" in res.lower()


def test_geocode_address_mock():
    """Test geocode_address with mocked Google Maps API response."""
    fake_api_data = {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Groningen, Netherlands",
                "geometry": {"location": {"lat": 53.2193, "lng": 6.5665}},
            }
        ],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_api_data

    with patch("requests.get", return_value=mock_resp):
        res = geocode_address("Groningen")
        assert "53.2193" in res
        assert "Groningen, Netherlands" in res


def test_get_live_weather_mock():
    """Test get_live_weather with mocked Open-Meteo response."""
    fake_geo_data = {
        "results": [
            {
                "name": "Groningen",
                "country": "Netherlands",
                "latitude": 53.2193,
                "longitude": 6.5665,
            }
        ]
    }
    fake_weather_data = {
        "current_weather": {
            "temperature": 18.5,
            "windspeed": 12.0,
            "weathercode": 1,
        }
    }

    def mock_get(url, *args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        if "geocoding-api" in url:
            mock_res.json.return_value = fake_geo_data
        else:
            mock_res.json.return_value = fake_weather_data
        return mock_res

    with patch("requests.get", side_effect=mock_get):
        res = get_live_weather(city="Groningen")
        assert "18.5°C" in res
        assert "Groningen" in res


def test_get_vibe_spots_mock():
    """Test get_vibe_spots with mocked Firestore client."""
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {
        "name": "Cozy Cafe",
        "city": "Groningen",
        "vibes": ["cozy"],
        "category": "Cafe",
        "neighborhood": "Center",
        "address": "Main St 1",
        "rating": 4.8,
        "price_level": "$$",
        "description": "A cozy cafe in Groningen.",
    }
    
    mock_db = MagicMock()
    mock_db.collection.return_value.stream.return_value = [mock_doc]

    with patch("app.agent._get_firestore_client", return_value=mock_db):
        res = get_vibe_spots(city="Groningen", vibe="cozy")
        assert "Cozy Cafe" in res


def test_execute_python_code_mock():
    """Test execute_python_code tool wrapping CodeExecutionInput."""
    mock_tool_ctx = MagicMock()
    mock_tool_ctx.invocation_context = MagicMock()

    mock_exec_result = MagicMock()
    mock_exec_result.stdout = "42\n"
    mock_exec_result.stderr = ""
    mock_exec_result.exception = None

    with patch("app.agent.code_executor") as mock_executor:
        mock_executor.execute_code.return_value = mock_exec_result
        res = execute_python_code("print(42)", mock_tool_ctx)
        assert "42" in res
