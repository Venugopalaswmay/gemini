# ruff: noqa
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

import json
import os
import urllib.request
import uuid
import requests
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.cloud import firestore, storage
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback

# Load local environment variables from .env file
load_dotenv()
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-01-d53bf4a69b0c")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-east1")

# Hardcoded GCP Project ID string as required for Firestore client
FIRESTORE_PROJECT = "qwiklabs-gcp-01-d53bf4a69b0c"
FIRESTORE_DATABASE = "vibe-db"
STORAGE_BUCKET_NAME = "vibe-now-media-qwiklabs-gcp-01-d53bf4a69b0c"

# Load Agent Engine resource name from deployment_metadata.json if available
DEPLOYMENT_METADATA_FILE = Path(__file__).parent.parent / "deployment_metadata.json"
AGENT_ENGINE_RESOURCE_NAME = "projects/995370310234/locations/us-east1/reasoningEngines/6705008823154769920"

if DEPLOYMENT_METADATA_FILE.exists():
    try:
        with open(DEPLOYMENT_METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            if metadata.get("remote_agent_runtime_id"):
                AGENT_ENGINE_RESOURCE_NAME = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

MEMORY_BANK_ID = AGENT_ENGINE_RESOURCE_NAME.split("/")[-1]

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME
)


def memory_service_builder() -> VertexAiMemoryBankService:
    """Builder returning a VertexAiMemoryBankService configured for this agent's Memory Bank."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract durable user facts and preferences into Memory Bank after each agent turn."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def _get_firestore_client() -> firestore.Client:
    """Helper to obtain a Firestore client with hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT, database=FIRESTORE_DATABASE)


def geocode_address(address: str) -> str:
    """Convert a human-readable street address or landmark into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The address or landmark to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        String containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={requests.utils.quote(address)}&key={api_key}"
        res = requests.get(url, timeout=5).json()

        if res.get("status") != "OK" or not res.get("results"):
            return f"Geocoding failed for address '{address}'. Status: {res.get('status')}"

        first = res["results"][0]
        formatted_address = first.get("formatted_address", address)
        location = first["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]

        return f"Geocoded Address: {formatted_address}\nLatitude: {lat}, Longitude: {lng}"
    except Exception as e:
        return f"Error during geocoding: {str(e)}"


def search_nearby_places(latitude: float, longitude: float, place_type: str = "cafe", radius_meters: float = 1000.0) -> str:
    """Find nearby places of a specific type (e.g. 'cafe', 'restaurant', 'park', 'bar', 'museum') near a latitude/longitude location using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of venue (e.g. 'cafe', 'restaurant', 'park', 'bar', 'museum', 'book_store').
        radius_meters: Radius distance search in meters (default 1000.0).

    Returns:
        Formatted string listing matching nearby places with name, formatted address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        payload = {
            "includedTypes": [place_type.lower().strip()],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        response = requests.post(url, json=payload, headers=headers, timeout=5)
        data = response.json()

        if response.status_code != 200 or "error" in data:
            err_msg = data.get("error", {}).get("message", response.text)
            return f"Places API (New) error: {err_msg}"

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found within {radius_meters}m radius."

        results = [f"Found {len(places)} nearby '{place_type}' place(s):"]
        for p in places:
            display_name = p.get("displayName", {}).get("text", "Unknown Name")
            address = p.get("formattedAddress", "N/A")
            loc = p.get("location", {})
            lat, lng = loc.get("latitude"), loc.get("longitude")

            results.append(
                f"• **{display_name}**\n"
                f"  Address: {address}\n"
                f"  Location: ({lat}, {lng})"
            )

        return "\n\n".join(results)
    except Exception as e:
        return f"Error querying Places API (New): {str(e)}"


def get_vibe_spots(city: Optional[str] = None, vibe: Optional[str] = None) -> str:
    """Search for spots in the Firestore database matching a city or vibe preference.

    Args:
        city: Optional city name (e.g. 'San Francisco', 'New York').
        vibe: Optional vibe keyword (e.g. 'cozy', 'chill', 'scenic', 'nightlife', 'nature').

    Returns:
        A string listing matching spot recommendations with details.
    """
    try:
        db = _get_firestore_client()
        docs = db.collection("vibe_spots").stream()
        results = []

        city_clean = city.lower().strip() if city else ""
        vibe_clean = vibe.lower().strip() if vibe else ""

        for doc in docs:
            data = doc.to_dict()
            doc_city = str(data.get("city", "")).lower()
            doc_vibes = [str(v).lower() for v in data.get("vibes", [])]

            # Filter logic
            if city_clean and city_clean not in doc_city and doc_city not in city_clean:
                continue
            if vibe_clean and not any(vibe_clean in v for v in doc_vibes):
                continue

            results.append(data)

        if not results:
            filter_desc = []
            if city:
                filter_desc.append(f"city '{city}'")
            if vibe:
                filter_desc.append(f"vibe '{vibe}'")
            filter_str = " and ".join(filter_desc) if filter_desc else "your criteria"
            return f"No vibe spots found matching {filter_str} in our database."

        formatted = [f"Found {len(results)} matching spot(s):"]
        for spot in results:
            vibes_str = ", ".join(spot.get("vibes", []))
            formatted.append(
                f"• **{spot.get('name')}** ({spot.get('category')}, {spot.get('neighborhood')}, {spot.get('city')})\n"
                f"  Rating: {spot.get('rating')} | Price: {spot.get('price_level')}\n"
                f"  Vibes: {vibes_str}\n"
                f"  Address: {spot.get('address')}\n"
                f"  Description: {spot.get('description')}"
            )
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error retrieving spots from database: {str(e)}"


def add_vibe_spot(
    name: str,
    city: str,
    neighborhood: str,
    vibes: List[str],
    category: str,
    description: str,
    address: str = "",
    price_level: str = "$$",
) -> str:
    """Add a new place or vibe spot into the Firestore database.

    Args:
        name: Name of the venue or place.
        city: City where the spot is located.
        neighborhood: Neighborhood or district name.
        vibes: List of vibe tags (e.g. ['cozy', 'coffee', 'chill']).
        category: Venue type (e.g. Cafe, Park, Rooftop Bar).
        description: A brief summary of why it fits the vibe.
        address: Street address.
        price_level: Price range indicator (e.g. $, $$, $$$, Free).

    Returns:
        Confirmation message with created spot ID.
    """
    try:
        db = _get_firestore_client()
        spot_id = f"spot_{city.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        spot_data = {
            "id": spot_id,
            "name": name,
            "city": city,
            "neighborhood": neighborhood,
            "vibes": vibes,
            "category": category,
            "rating": 5.0,
            "address": address,
            "description": description,
            "price_level": price_level,
        }
        db.collection("vibe_spots").document(spot_id).set(spot_data)
        return f"✓ Successfully added '{name}' ({spot_id}) to the Vibe Now database!"
    except Exception as e:
        return f"Error adding spot to database: {str(e)}"


def upload_media_asset(file_name: str, content: str) -> str:
    """Upload media content, destination notes, or postcard text to the public Cloud Storage bucket.

    Args:
        file_name: Name of the file to save (e.g. 'sf_cozy_postcard.txt', 'spot_banner.svg').
        content: The text content, SVG markup, or data to store.

    Returns:
        Public HTTPS URL of the uploaded asset.
    """
    try:
        client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(file_name)
        content_type = "image/svg+xml" if file_name.endswith(".svg") else "text/plain"
        blob.upload_from_string(content, content_type=content_type)
        return f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{file_name}"
    except Exception as e:
        return f"Error uploading asset to Cloud Storage: {str(e)}"


def get_live_weather(city: str) -> str:
    """Fetch real-time weather, temperature, and atmospheric conditions for a city using Open-Meteo public API.

    Args:
        city: Name of the target city (e.g. 'San Francisco', 'New York', 'Tokyo').

    Returns:
        String summary of live weather conditions and temperature.
    """
    api_key = os.environ.get("OPEN_WEATHER_API_KEY", None)

    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_res = requests.get(geo_url, timeout=5).json()

        if not geo_res.get("results"):
            return f"Could not find geographic location for '{city}'."

        place = geo_res["results"][0]
        lat, lon = place["latitude"], place["longitude"]
        place_name = place.get("name", city)
        country = place.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(weather_url, timeout=5).json()
        curr = w_res.get("current_weather", {})

        temp = curr.get("temperature")
        wind = curr.get("windspeed")
        wcode = curr.get("weathercode", 0)

        weather_desc = "Clear/Sunny"
        if wcode in [1, 2, 3]:
            weather_desc = "Partly Cloudy"
        elif wcode in [45, 48]:
            weather_desc = "Foggy"
        elif wcode in [51, 53, 55, 61, 63, 65]:
            weather_desc = "Rainy"
        elif wcode >= 71:
            weather_desc = "Snowy/Stormy"

        return f"Live weather for {place_name}, {country}: {temp}°C, {weather_desc}, wind speed {wind} km/h."
    except Exception as e:
        return f"Error retrieving weather data: {str(e)}"


def generate_vibe_image(prompt: str, tool_context: ToolContext) -> str:
    """Generate a destination postcard or vibe image for a recommended place using gemini-3.1-flash-lite-image in the global region, save as an artifact, and upload to public Cloud Storage.

    Args:
        prompt: Description of the scene or postcard image to generate (e.g. 'A cozy sunlit bookstore cafe in San Francisco Mission District').

    Returns:
        Public HTTPS URL of the generated image uploaded to Cloud Storage.
    """
    try:
        # 1. Instantiate Vertex AI Client in global region with project ID
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")

        # 2. Call gemini-3.1-flash-lite-image model
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"Generate a beautiful travel vibe postcard image of: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return "Error: Image model did not return image bytes."

        ext = ".jpg" if "jpeg" in mime_type else ".png"
        filename = f"vibe_image_{uuid.uuid4().hex[:8]}{ext}"

        # (1) Save artifact in Playground via tool_context
        tool_context.save_artifact(
            filename=filename,
            artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        )

        # (2) Upload same image bytes directly to public Cloud Storage bucket
        gcs_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = gcs_client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating vibe image: {str(e)}"


def generate_vibe_video(prompt: str, tool_context: ToolContext) -> str:
    """Generate a short video snippet highlighting a place, venue, or vibe using gemini-omni-flash-preview in the global region, save as an artifact, and upload to public Cloud Storage.

    Args:
        prompt: Description of the scene or video snippet to generate (e.g. 'A short video tour of a cozy cafe in Groningen with warm ambient lighting').

    Returns:
        Public HTTPS URL of the generated video uploaded to Cloud Storage.
    """
    try:
        # 1. Instantiate Vertex AI Client in global region with project ID
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")

        # 2. Call gemini-omni-flash-preview model for video generation
        response = client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=f"Generate a short video snippet of: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["VIDEO"]
            )
        )

        video_bytes = None
        mime_type = "video/mp4"

        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "video/mp4"
                    break

        if not video_bytes:
            return "Error: Video model did not return video bytes."

        ext = ".mp4" if "mp4" in mime_type else ".webm"
        filename = f"vibe_video_{uuid.uuid4().hex[:8]}{ext}"

        # (1) Save artifact in Playground via tool_context
        tool_context.save_artifact(
            filename=filename,
            artifact=types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        )

        # (2) Upload same video bytes directly to public Cloud Storage bucket
        gcs_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = gcs_client.bucket(STORAGE_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating vibe video: {str(e)}"


def execute_python_code(code: str, tool_context: ToolContext) -> str:
    """Execute Python code in a secure Agent Engine sandbox environment.

    Args:
        code: The Python code string to execute.
    """
    try:
        from google.adk.code_executors.code_execution_utils import CodeExecutionInput
        code_input = CodeExecutionInput(code=code)
        res = code_executor.execute_code(
            invocation_context=tool_context.invocation_context,
            code_execution_input=code_input,
        )
        output = []
        if res.stdout:
            output.append(f"STDOUT:\n{res.stdout}")
        if res.stderr:
            output.append(f"STDERR:\n{res.stderr}")
        if res.exception:
            output.append(f"EXCEPTION:\n{res.exception}")
        return "\n".join(output) if output else "Code executed successfully with no output."
    except Exception as e:
        return f"Error executing python code: {str(e)}"


def get_current_location() -> str:
    """Detect the current geographic location of the system based on public IP address.

    Returns:
        A string describing the detected city, region, country, and coordinates, or a failure message.
    """
    try:
        url = "http://ip-api.com/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                lat = data.get("lat")
                lon = data.get("lon")
                return f"Detected system location: {city}, {region}, {country} (Coordinates: {lat}, {lon})"
    except Exception:
        pass

    try:
        url = "https://ipapi.co/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            city = data.get("city", "")
            region = data.get("region", "")
            country = data.get("country_name", "")
            lat = data.get("latitude")
            lon = data.get("longitude")
            if city or lat:
                return f"Detected system location: {city}, {region}, {country} (Coordinates: {lat}, {lon})"
    except Exception as e:
        return f"Could not detect system location: {str(e)}"

    return "Could not automatically detect system location. Please ask the user to specify their location."


a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are Vibe Now, an expert instant travel guide and local atmosphere assistant. "
        "Your mission is to help travelers and locals discover places based on their current location and desired mood/vibe. "
        "You remember traveler preferences, dietary needs, all user allergies (food, environmental, contact, or medical), budget choices, and past visited places across conversations. "
        "CRITICAL ALLERGY & MEMORY DIRECTIVE: Always remember and track any allergies stated by the user. "
        "When recommending places, food, drinks, or activities, cross-reference the user's remembered allergies and strictly avoid any venue or option that poses an allergy risk. "
        "LOCATION DETECTION DIRECTIVE: When location is needed and not provided by the user, invoke `get_current_location` to detect the system's current geographic location. "
        "If `get_current_location` fails or does not return valid location details, ask the user politely to specify their location (e.g., city, address, or neighborhood). "
        "Use `generate_vibe_image` to generate travel postcard images for recommended places. "
        "Use `generate_vibe_video` to generate short video highlights for recommended places or vibes. "
        "Use `geocode_address` to convert addresses or landmarks into latitude and longitude coordinates. "
        "Use `search_nearby_places` to search for nearby places using Google Places API (New). "
        "Use `get_live_weather` to check real-time weather for destinations. "
        "Use `get_vibe_spots` to search for matching curated places in the database. "
        "Use `add_vibe_spot` when users want to save or share a new venue recommendation. "
        "Use `upload_media_asset` to save travel notes or postcards to Cloud Storage. "
        "Use `execute_python_code` when you need to execute Python code in the sandbox. Do not invoke google:python_interpreter."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "CRITICAL FORMAT REQUIREMENT: Output MUST be a JSON array containing BOTH a `beginRendering` object specifying the root Card ID and a `surfaceUpdate` object defining all components. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> or <a2ui-json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        get_current_location,
        geocode_address,
        search_nearby_places,
        get_vibe_spots,
        add_vibe_spot,
        upload_media_asset,
        get_live_weather,
        generate_vibe_image,
        generate_vibe_video,
        execute_python_code,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
