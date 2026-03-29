"""
02_geocode.py

Builds geocoded_locations.json: a lookup from "city|state|country" -> {lat, lon, geo_source}.

Pass 1: GeoNames cities1000.txt (offline, fast)
Pass 2: Nominatim API (online, slow, rate-limited to 1 req/sec, with persistent cache)

Outputs:
  pipeline/geocoded_locations.json
  pipeline/geocode_failures.csv
"""

import csv
import json
import time
import unicodedata
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from tqdm import tqdm

PIPELINE_DIR = Path(__file__).parent
RAW_DIR = PIPELINE_DIR / "raw"
GEONAMES_FILE = RAW_DIR / "geonames" / "cities1000.txt"
PEOPLE_FILE = RAW_DIR / "baseballdatabank" / "core" / "People.csv"
SCHOOLS_FILE = RAW_DIR / "baseballdatabank" / "core" / "Schools.csv"
OUTPUT_FILE = PIPELINE_DIR / "geocoded_locations.json"
CACHE_FILE = PIPELINE_DIR / "geocode_cache.json"
FAILURES_FILE = PIPELINE_DIR / "geocode_failures.csv"

# Lahman uses non-standard country names. Map to ISO 2-letter codes for GeoNames lookup.
COUNTRY_MAP = {
    "USA": "US",
    "D.R.": "DO",
    "Dominican Republic": "DO",
    "Puerto Rico": "PR",
    "Cuba": "CU",
    "Venezuela": "VE",
    "Panama": "PA",
    "Mexico": "MX",
    "Canada": "CA",
    "Japan": "JP",
    "South Korea": "KR",
    "Korea": "KR",
    "Australia": "AU",
    "Colombia": "CO",
    "Nicaragua": "NI",
    "Virgin Islands": "VI",
    "Bahamas": "BS",
    "Curacao": "CW",
    "Aruba": "AW",
    "Netherlands": "NL",
    "Germany": "DE",
    "Italy": "IT",
    "France": "FR",
    "Spain": "ES",
    "United Kingdom": "GB",
    "England": "GB",
    "Scotland": "GB",
    "Ireland": "IE",
    "Poland": "PL",
    "Russia": "RU",
    "Czechoslovakia": "CZ",
    "Czech Republic": "CZ",
    "Slovakia": "SK",
    "Austria": "AT",
    "Hungary": "HU",
    "Yugoslavia": "RS",
    "Serbia": "RS",
    "Croatia": "HR",
    "Ukraine": "UA",
    "Lithuania": "LT",
    "Latvia": "LV",
    "Estonia": "EE",
    "Finland": "FI",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Belgium": "BE",
    "Switzerland": "CH",
    "Portugal": "PT",
    "Greece": "GR",
    "Turkey": "TR",
    "Israel": "IL",
    "Philippines": "PH",
    "Taiwan": "TW",
    "China": "CN",
    "Brazil": "BR",
    "Argentina": "AR",
    "Chile": "CL",
    "Peru": "PE",
    "Honduras": "HN",
    "Guatemala": "GT",
    "El Salvador": "SV",
    "Costa Rica": "CR",
    "Jamaica": "JM",
    "Trinidad": "TT",
    "Trinidad and Tobago": "TT",
    "Haiti": "HT",
    "Cayman Islands": "KY",
    "Barbados": "BB",
}


def normalize(s: str) -> str:
    """Lowercase, remove accents, strip whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def build_geonames_lookup(geonames_file: Path) -> dict:
    """Build lookup dict from GeoNames cities1000.txt.

    Keys: (city_norm, country_code2) and (city_norm, state_code, "US") for US cities.
    Value: (lat, lon)
    """
    lookup = {}
    print("Building GeoNames lookup table (pass 1: main names)...")
    with open(geonames_file, encoding="utf-8") as f:
        for line in tqdm(f, desc="GeoNames rows"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15:
                continue
            name = parts[1]
            ascii_name = parts[2]
            lat = float(parts[4])
            lon = float(parts[5])
            country = parts[8]
            state = parts[10]

            for city_name in {name, ascii_name}:
                key = (normalize(city_name), country)
                if key not in lookup:
                    lookup[key] = (lat, lon)
                if country == "US":
                    us_key = (normalize(city_name), state, "US")
                    if us_key not in lookup:
                        lookup[us_key] = (lat, lon)

    print("Building GeoNames lookup table (pass 2: alternate names)...")
    with open(geonames_file, encoding="utf-8") as f:
        for line in tqdm(f, desc="GeoNames alternates"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15:
                continue
            lat = float(parts[4])
            lon = float(parts[5])
            country = parts[8]
            state = parts[10]
            alternates = parts[3].split(",") if parts[3] else []
            for alt in alternates:
                alt = alt.strip()
                if not alt:
                    continue
                key = (normalize(alt), country)
                if key not in lookup:
                    lookup[key] = (lat, lon)
                if country == "US":
                    us_key = (normalize(alt), state, "US")
                    if us_key not in lookup:
                        lookup[us_key] = (lat, lon)

    print(f"GeoNames lookup: {len(lookup):,} entries")
    return lookup


def resolve_geonames(city: str, state: str, country: str, lookup: dict):
    """Try to resolve a city/state/country to (lat, lon) via GeoNames lookup."""
    if not city or not country:
        return None
    cc2 = COUNTRY_MAP.get(country, country.upper()[:2])
    city_norm = normalize(city)

    if cc2 == "US" and state:
        key = (city_norm, state.upper(), "US")
        if key in lookup:
            return lookup[key]

    key = (city_norm, cc2)
    if key in lookup:
        return lookup[key]

    return None


def resolve_nominatim(city: str, state: str, country: str, geolocator, cache: dict):
    """Resolve via Nominatim with persistent cache. Rate-limited to 1 req/sec."""
    cache_key = f"{city}|{state}|{country}"
    if cache_key in cache:
        val = cache[cache_key]
        return (val["lat"], val["lon"]) if val else None

    query = ", ".join(filter(None, [city, state, country]))
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
        print(f"  Nominatim error for '{query}': {e}")
        cache[cache_key] = None
        return None


def extract_location_triples(people_df: pd.DataFrame, schools_df) -> list:
    triples = set()
    for _, row in people_df.iterrows():
        for prefix in ["birth", "death"]:
            city = str(row.get(f"{prefix}City", "") or "").strip()
            state = str(row.get(f"{prefix}State", "") or "").strip()
            country = str(row.get(f"{prefix}Country", "") or "").strip()
            if city and country:
                triples.add((city, state, country))

    if schools_df is not None:
        for _, row in schools_df.iterrows():
            city = str(row.get("city", "") or "").strip()
            state = str(row.get("state", "") or "").strip()
            if city and state:
                triples.add((city, state, "USA"))

    return list(triples)


def main():
    print("Loading People.csv...")
    people_df = pd.read_csv(PEOPLE_FILE, low_memory=False)

    schools_df = None
    if SCHOOLS_FILE.exists():
        print("Loading Schools.csv...")
        schools_df = pd.read_csv(SCHOOLS_FILE, low_memory=False)

    triples = extract_location_triples(people_df, schools_df)
    print(f"Unique location triples to resolve: {len(triples):,}")

    geonames_lookup = build_geonames_lookup(GEONAMES_FILE)

    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f"Loaded {len(cache):,} cached Nominatim results")

    results = {}
    misses = []

    print("\nPass 1: GeoNames lookup...")
    for city, state, country in tqdm(triples):
        key = f"{city}|{state}|{country}"
        coords = resolve_geonames(city, state, country, geonames_lookup)
        if coords:
            results[key] = {"lat": round(coords[0], 5), "lon": round(coords[1], 5), "geo_source": "geonames"}
        else:
            misses.append((city, state, country))

    print(f"  Resolved: {len(results):,} / {len(triples):,} ({len(misses):,} misses)")

    if misses:
        print(f"\nPass 2: Nominatim fallback for {len(misses):,} misses (~{len(misses) // 60 + 1} min)...")
        geolocator = Nominatim(user_agent="claudeball-baseball-heatmap/1.0")
        for city, state, country in tqdm(misses):
            key = f"{city}|{state}|{country}"
            coords = resolve_nominatim(city, state, country, geolocator, cache)
            if coords:
                results[key] = {"lat": round(coords[0], 5), "lon": round(coords[1], 5), "geo_source": "nominatim"}
            else:
                results[key] = None

        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
        print(f"  Saved Nominatim cache ({len(cache):,} entries)")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f)
    print(f"\nWrote {len(results):,} entries to {OUTPUT_FILE}")

    failures = [(c, s, co) for c, s, co in triples if results.get(f"{c}|{s}|{co}") is None]
    with open(FAILURES_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "state", "country"])
        writer.writerows(failures)
    print(f"Failed to geocode {len(failures):,} locations -> {FAILURES_FILE}")


if __name__ == "__main__":
    main()
