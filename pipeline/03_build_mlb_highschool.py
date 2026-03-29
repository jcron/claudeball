"""
03_build_mlb_highschool.py

Fetches high school data from MLB Stats API for players who debuted 1960+.
Parses the freeform 'highSchool' string field and geocodes it.

Outputs:
  pipeline/highschool_geo.json   -- { playerID: {lat, lon, school, city, state} }
"""

import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from geopy.geocoders import Nominatim
from tqdm import tqdm

PIPELINE_DIR = Path(__file__).parent
RAW_DIR = PIPELINE_DIR / "raw"
PEOPLE_FILE = RAW_DIR / "baseballdatabank" / "core" / "People.csv"
OUTPUT_FILE = PIPELINE_DIR / "highschool_geo.json"
CACHE_FILE = PIPELINE_DIR / "geocode_cache.json"

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
BATCH_SIZE = 500
MIN_DEBUT_YEAR = 1960

HS_PATTERNS = [
    re.compile(r"^(.+?),\s*([A-Za-z\s.'\-]+),\s*([A-Z]{2})$"),
    re.compile(r"^(.+?);\s*([A-Za-z\s.'\-]+),\s*([A-Z]{2})$"),
    re.compile(r"^([A-Za-z\s.'\-]+),\s*([A-Z]{2})$"),
]


def parse_high_school(hs_str: str):
    if not hs_str or not isinstance(hs_str, str):
        return None
    hs_str = hs_str.strip()
    for pattern in HS_PATTERNS:
        m = pattern.match(hs_str)
        if m:
            groups = m.groups()
            if len(groups) == 3:
                return {"school": groups[0].strip(), "city": groups[1].strip(), "state": groups[2].strip()}
            elif len(groups) == 2:
                return {"school": None, "city": groups[0].strip(), "state": groups[1].strip()}
    return None


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def geocode_city_state(city: str, state: str, geolocator, cache: dict):
    cache_key = f"{city}|{state}|USA"
    if cache_key in cache:
        val = cache[cache_key]
        return (val["lat"], val["lon"]) if val else None
    query = f"{city}, {state}, USA"
    try:
        time.sleep(1.1)
        loc = geolocator.geocode(query, timeout=10)
        if loc:
            cache[cache_key] = {"lat": loc.latitude, "lon": loc.longitude}
            return (loc.latitude, loc.longitude)
        else:
            cache[cache_key] = None
            return None
    except Exception as e:
        print(f"  Geocode error for '{query}': {e}")
        cache[cache_key] = None
        return None


def fetch_mlb_api_batch(player_ids: list) -> dict:
    ids_str = ",".join(str(i) for i in player_ids)
    url = f"{MLB_API_BASE}/people"
    params = {"personIds": ids_str, "fields": "people,id,fullName,highSchool"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {str(p["id"]): p.get("highSchool") for p in data.get("people", [])}
    except Exception as e:
        print(f"  MLB API error: {e}")
        return {}


def main():
    print("Loading People.csv...")
    people_df = pd.read_csv(PEOPLE_FILE, low_memory=False)

    # Check if MLBAM IDs are present
    if "key_mlbam" not in people_df.columns:
        print("No key_mlbam column in People.csv — skipping MLB Stats API lookup.")
        print("Writing empty highschool_geo.json")
        with open(OUTPUT_FILE, "w") as f:
            json.dump({}, f)
        return

    # Filter to players with MLBAM ID and debut >= MIN_DEBUT_YEAR
    def debut_year(val):
        s = str(val or "")
        return int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else 0

    modern = people_df[
        people_df["key_mlbam"].notna() &
        people_df["debut"].apply(debut_year) >= MIN_DEBUT_YEAR
    ].copy()

    if modern.empty:
        print("No modern players with MLBAM IDs found. Writing empty highschool_geo.json")
        with open(OUTPUT_FILE, "w") as f:
            json.dump({}, f)
        return

    mlbam_ids = modern["key_mlbam"].astype(int).tolist()
    player_id_map = dict(zip(modern["key_mlbam"].astype(int), modern["playerID"]))

    print(f"Fetching high school data for {len(mlbam_ids):,} modern players from MLB Stats API...")
    hs_raw = {}
    for i in tqdm(range(0, len(mlbam_ids), BATCH_SIZE), desc="MLB API batches"):
        batch = mlbam_ids[i: i + BATCH_SIZE]
        hs_raw.update(fetch_mlb_api_batch(batch))
        time.sleep(0.5)

    non_null = sum(1 for v in hs_raw.values() if v)
    print(f"  Retrieved {non_null:,} non-null high school entries")

    cache = load_cache()
    geolocator = Nominatim(user_agent="claudeball-baseball-heatmap/1.0")

    results = {}
    for mlbam_id_str, hs_str in tqdm(hs_raw.items(), desc="Geocoding high schools"):
        player_id = player_id_map.get(int(mlbam_id_str))
        if not player_id or not hs_str:
            continue
        parsed = parse_high_school(hs_str)
        if not parsed:
            continue
        city = parsed.get("city", "")
        state = parsed.get("state", "")
        if not city or not state:
            continue
        coords = geocode_city_state(city, state, geolocator, cache)
        if coords:
            results[player_id] = {
                "lat": round(coords[0], 5),
                "lon": round(coords[1], 5),
                "school": parsed.get("school"),
                "city": city,
                "state": state,
                "confidence": "high",
            }

    save_cache(cache)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)
    print(f"\nWrote {len(results):,} high school entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
