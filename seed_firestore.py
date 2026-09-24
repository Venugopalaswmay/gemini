"""
Seed script for Vibe Now Firestore collection 'vibe_spots'.
"""
import sys
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPIError

FIRESTORE_PROJECT = "qwiklabs-gcp-01-d53bf4a69b0c"
FIRESTORE_DATABASE = "vibe-db"

SEED_SPOTS = [
    {
        "id": "spot_sf_01",
        "name": "The Sunlit Cafe & Books",
        "city": "San Francisco",
        "neighborhood": "Mission District",
        "vibes": ["cozy", "chill", "coffee", "reading", "quiet"],
        "category": "Cafe",
        "rating": 4.8,
        "address": "542 Valencia St, San Francisco, CA",
        "description": "Warm, sunlit corner bookstore cafe with specialty pour-overs and comfortable leather armchairs.",
        "price_level": "$$"
    },
    {
        "id": "spot_sf_02",
        "name": "Fog City Rooftop & Lounge",
        "city": "San Francisco",
        "neighborhood": "Financial District",
        "vibes": ["energetic", "romantic", "cocktails", "nightlife", "scenic"],
        "category": "Rooftop Bar",
        "rating": 4.6,
        "address": "222 Battery St, San Francisco, CA",
        "description": "Panoramic skyline views, craft botanical cocktails, and heated outdoor fire pits.",
        "price_level": "$$$"
    },
    {
        "id": "spot_sf_03",
        "name": "Golden Gate Tea Garden & Sanctuary",
        "city": "San Francisco",
        "neighborhood": "Golden Gate Park",
        "vibes": ["chill", "nature", "peaceful", "outdoors", "zen"],
        "category": "Tea House",
        "rating": 4.9,
        "address": "75 Hagiwara Tea Garden Rd, San Francisco, CA",
        "description": "Tranquil Japanese garden with stepping stones, koi ponds, and traditional matcha tastings.",
        "price_level": "$$"
    },
    {
        "id": "spot_ny_01",
        "name": "Village Speakeasy & Jazz Cellar",
        "city": "New York",
        "neighborhood": "Greenwich Village",
        "vibes": ["cozy", "nightlife", "romantic", "music", "speakeasy"],
        "category": "Jazz Club",
        "rating": 4.7,
        "address": "130 MacDougal St, New York, NY",
        "description": "Intimate subterranean jazz sanctuary featuring craft vintage cocktails and live acoustic sets.",
        "price_level": "$$$"
    },
    {
        "id": "spot_ny_02",
        "name": "High Line Promenade & Art Promenade",
        "city": "New York",
        "neighborhood": "Chelsea",
        "vibes": ["energetic", "outdoors", "scenic", "art", "walking"],
        "category": "Park",
        "rating": 4.8,
        "address": "Gansevoort St & Washington St, New York, NY",
        "description": "Elevated park built on a historic freight rail line featuring native garden design and Hudson River views.",
        "price_level": "Free"
    }
]


def seed_database():
    print(f"Connecting to Firestore project '{FIRESTORE_PROJECT}', database '{FIRESTORE_DATABASE}'...")
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT, database=FIRESTORE_DATABASE)
        collection_ref = db.collection("vibe_spots")
        
        for spot in SEED_SPOTS:
            doc_ref = collection_ref.document(spot["id"])
            doc_ref.set(spot)
            print(f"  ✓ Seeded spot: {spot['name']} ({spot['id']}) in city '{spot['city']}'")
            
        print("\n🎉 Firestore database successfully seeded with initial vibe_spots!")
    except Exception as e:
        print(f"❌ Error seeding Firestore: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
