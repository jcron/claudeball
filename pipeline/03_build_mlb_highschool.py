"""
03_build_mlb_highschool.py

Fetches high school data from MLB Stats API for players who debuted 1960+.
Uses the Chadwick Bureau Register to cross-reference Baseball Databank playerIDs
to MLBAM IDs (key_mlbam), then calls the MLB Stats API highSchool field.

Outputs:
  pipeline/highschool_geo.json   -- { playerID: {lat, lon, school, city, state} }
"""

import io
import json
import re
import time
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd
import requests
from geopy.geocoders import Nominatim
from tqdm import tqdm

PIPELINE_DIR = Path(__file__).parent
RAW_DIR = PIPELINE_DIR / "raw"
PEOPLE_FILE = RAW_DIR / "baseballdatabank" / "core" / "People.csv"
CHADWICK_DIR = RAW_DIR / "chadwick"
OUTPUT_FILE = PIPELINE_DIR / "highschool_geo.json"
CACHE_FILE = PIPELINE_DIR / "geocode_cache.json"
GEONAMES_FILE = RAW_DIR / "geonames" / "cities1000.txt"

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
BATCH_SIZE = 500
MIN_DEBUT_YEAR = 1960

# Chadwick Register — single CSV with all player IDs cross-referenced
CHADWICK_URL = "https://github.com/chadwickbureau/register/archive/refs/heads/master.zip"

HS_PATTERNS = [
    re.compile(r"^(.+?),\s*([A-Za-z\s.\-']+),\s*([A-Z]{2})$"),
    re.compile(r"^(.+?);\s*([A-Za-z\s.\-']+),\s*([A-Z]{2})$"),
    re.compile(r"^([A-Za-z\s.\-']+),\s*([A-Z]{2})$"),
]


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def download_chadwick_register() -> pd.DataFrame:
    """Download Chadwick Bureau Register and return as DataFrame with key_bbref + key_mlbam."""
    CHADWICK_DIR.mkdir(parents=True, exist_ok=True)
    register_file = CHADWICK_DIR / "register.csv"

    if register_file.exists():
        print(f"  Chadwick register already at {register_file}, loading...")
        return pd.read_csv(register_file, low_memory=False)

    print("  Downloading Chadwick Bureau Register (~50MB)...")
    resp = requests.get(CHADWICK_URL, timeout=120, stream=True)
    resp.raise_for_status()
    content = b""
    for chunk in resp.iter_content(chunk_size=65536):
        content += chunk
    print(f"  Downloaded {len(content) / 1e6:.1f} MB")

    # The zip contains register-master/data/people/*.csv — concatenate all
    dfs = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        csv_files = [f for f in zf.namelist() if f.startswith("register-master/data/people") and f.endswith(".csv")]
        print(f"  Found {len(csv_files)} register CSV files")
        for csv_file in csv_files:
            with zf.open(csv_file) as f:
                df = pd.read_csv(f, low_memory=False)
                dfs.append(df)

    if not dfs:
        raise RuntimeError("No CSV files found in Chadwick Register zip")

    register = pd.concat(dfs, ignore_index=True)
    register.to_csv(register_file, index=False)
    print(f"  Saved {len(register):,} register entries to {register_file}")
    return register


def build_geonames_us_lookup() -> dict:
    """Build a (city_norm, state, 'US') -> (lat, lon) lookup for US cities."""
    lookup = {}
    with open(GEONAMES_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15 or parts[8] != "US":
                continue
            lat, lon = float(parts[4]), float(parts[5])
            state = parts[10]
            for name in {parts[1], parts[2]}:
                key = (normalize(name), state, "US")
                if key not in lookup:
                    lookup[key] = (lat, lon)
    return lookup


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


def geocode_city_state(city: str, state: str, gn_lookup: dict, geolocator, cache: dict):
    key = normalize(city)
    gn_key = (key, state.upper(), "US")
    if gn_key in gn_lookup:
        lat, lon = gn_lookup[gn_key]
        return (lat, lon)

    cache_key = f"{city}|{state}|USA"
    if cache_key in cache:
        val = cache[cache_key]
        return (val["lat"], val["lon"]) if val else None

    time.sleep(1.1)
    try:
        loc = geolocator.geocode(f"{city}, {state}, USA", timeout=10)
        if loc:
            cache[cache_key] = {"lat": loc.latitude, "lon": loc.longitude}
            return (loc.latitude, loc.longitude)
        else:
            cache[cache_key] = None
            return None
    except Exception as e:
        print(f"  Geocode error for '{city}, {state}': {e}")
        cache[cache_key] = None
        return None


def fetch_mlb_api_batch(mlbam_ids: list) -> dict:
    """Returns {mlbam_id_str: {"name": ..., "city": ..., "state": ...} | None}"""
    ids_str = ",".join(str(i) for i in mlbam_ids)
    params = {"personIds": ids_str, "hydrate": "education"}
    try:
        resp = requests.get(f"{MLB_API_BASE}/people", params=params, timeout=15)
        resp.raise_for_status()
        result = {}
        for p in resp.json().get("people", []):
            edu = p.get("education") or {}
            hs_list = edu.get("highschools") or []
            result[str(p["id"])] = hs_list[0] if hs_list else None
        return result
    except Exception as e:
        print(f"  MLB API error: {e}")
        return {}


def main():
    print("Loading People.csv...")
    people_df = pd.read_csv(PEOPLE_FILE, low_memory=False)

    def debut_year(val):
        s = str(val or "")
        return int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else 0

    modern_players = people_df[people_df["debut"].apply(debut_year) >= MIN_DEBUT_YEAR].copy()
    print(f"  {len(modern_players):,} players with debut >= {MIN_DEBUT_YEAR}")

    print("Downloading Chadwick Bureau Register for MLBAM ID crosswalk...")
    register = download_chadwick_register()

    # Build bbref_id -> mlbam_id mapping
    id_cols = [c for c in ["key_bbref", "key_mlbam"] if c in register.columns]
    if len(id_cols) < 2:
        print(f"  ERROR: Register columns: {register.columns.tolist()}")
        print("  Writing empty highschool_geo.json")
        with open(OUTPUT_FILE, "w") as f:
            json.dump({}, f)
        return

    crosswalk = register[["key_bbref", "key_mlbam"]].dropna()
    crosswalk = crosswalk[crosswalk["key_mlbam"] != 0]
    bbref_to_mlbam = dict(zip(crosswalk["key_bbref"], crosswalk["key_mlbam"].astype(int)))
    print(f"  {len(bbref_to_mlbam):,} bbref->mlbam mappings")

    # Map modern players to MLBAM IDs
    modern_players["mlbam_id"] = modern_players["playerID"].map(bbref_to_mlbam)
    mapped = modern_players[modern_players["mlbam_id"].notna()].copy()
    print(f"  {len(mapped):,} modern players mapped to MLBAM IDs")

    mlbam_ids = mapped["mlbam_id"].astype(int).tolist()
    player_id_map = dict(zip(mapped["mlbam_id"].astype(int), mapped["playerID"]))

    print(f"Fetching high school data from MLB Stats API ({len(mlbam_ids):,} players)...")
    hs_raw = {}
    for i in tqdm(range(0, len(mlbam_ids), BATCH_SIZE), desc="MLB API batches"):
        batch = mlbam_ids[i: i + BATCH_SIZE]
        hs_raw.update(fetch_mlb_api_batch(batch))
        time.sleep(0.3)

    non_null = sum(1 for v in hs_raw.values() if v)
    print(f"  {non_null:,} players have high school data")

    print("Building GeoNames US city lookup...")
    gn_lookup = build_geonames_us_lookup()

    cache = load_cache()
    geolocator = Nominatim(user_agent="claudeball-baseball-heatmap/1.0")

    results = {}
    nominatim_needed = 0
    for mlbam_id_str, hs_data in tqdm(hs_raw.items(), desc="Geocoding high schools"):
        if not hs_data:
            continue
        player_id = player_id_map.get(int(mlbam_id_str))
        if not player_id:
            continue
        city = str(hs_data.get("city") or "").strip()
        state = str(hs_data.get("state") or "").strip()
        school = str(hs_data.get("name") or "").strip() or None
        if not city or not state:
            continue

        gn_key = (normalize(city), state.upper(), "US")
        if gn_key not in gn_lookup:
            nominatim_needed += 1

        coords = geocode_city_state(city, state, gn_lookup, geolocator, cache)
        if coords:
            results[player_id] = {
                "lat": round(coords[0], 5),
                "lon": round(coords[1], 5),
                "school": school,
                "city": city,
                "state": state,
            }

    save_cache(cache)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)
    print(f"\nWrote {len(results):,} high school entries to {OUTPUT_FILE}")
    if nominatim_needed:
        print(f"  ({nominatim_needed} cities looked up via Nominatim)")


if __name__ == "__main__":
    main()
