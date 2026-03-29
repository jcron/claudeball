"""
04_build_dataset.py

Merges all data sources into the final JSON files consumed by the frontend.

Outputs (to public/data/):
  players.json           -- array of player objects with geocoded locations
  team_year_index.json   -- { franchID: { year: [playerID, ...] } }
  meta.json              -- franchise list + global year bounds
  population_points.json -- [[lon, lat, population], ...] from GeoNames cities1000
"""

import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

PIPELINE_DIR = Path(__file__).parent
RAW_DIR = PIPELINE_DIR / "raw"
OUTPUT_DIR = PIPELINE_DIR.parent / "public" / "data"

PEOPLE_FILE = RAW_DIR / "baseballdatabank" / "core" / "People.csv"
APPEARANCES_FILE = RAW_DIR / "baseballdatabank" / "core" / "Appearances.csv"
TEAMS_FILE = RAW_DIR / "baseballdatabank" / "core" / "Teams.csv"
COLLEGE_FILE = RAW_DIR / "baseballdatabank" / "core" / "CollegePlaying.csv"
SCHOOLS_FILE = RAW_DIR / "baseballdatabank" / "core" / "Schools.csv"
GEONAMES_FILE = RAW_DIR / "geonames" / "cities1000.txt"

GEOCODED_FILE = PIPELINE_DIR / "geocoded_locations.json"
HIGHSCHOOL_FILE = PIPELINE_DIR / "highschool_geo.json"


def load_geocoded() -> dict:
    with open(GEOCODED_FILE) as f:
        return json.load(f)


def lookup_geo(city: str, state: str, country: str, geocoded: dict):
    if not city or not country:
        return None
    key = f"{city}|{state}|{country}"
    return geocoded.get(key)


def build_population_points(geonames_file: Path) -> list:
    points = []
    print("Building population points from GeoNames...")
    with open(geonames_file, encoding="utf-8") as f:
        for line in tqdm(f, desc="GeoNames rows"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15:
                continue
            try:
                lat = float(parts[4])
                lon = float(parts[5])
                population = int(parts[14]) if parts[14] else 0
                if population > 0:
                    points.append([round(lon, 4), round(lat, 4), population])
            except (ValueError, IndexError):
                continue
    print(f"  {len(points):,} population points")
    return points


def build_school_geo(geocoded: dict) -> dict:
    if not SCHOOLS_FILE.exists():
        return {}
    schools_df = pd.read_csv(SCHOOLS_FILE, low_memory=False)
    result = {}
    for _, row in schools_df.iterrows():
        school_id = row.get("schoolID") or row.get("schoolId")
        if not school_id:
            continue
        city = str(row.get("city", "") or "").strip()
        state = str(row.get("state", "") or "").strip()
        name = str(row.get("name_full", "") or row.get("schoolName", "") or "").strip()
        if city and state:
            geo = lookup_geo(city, state, "USA", geocoded)
            if geo:
                result[school_id] = {"lat": geo["lat"], "lon": geo["lon"], "name": name}
    return result


def build_college_map(school_geo: dict) -> dict:
    if not COLLEGE_FILE.exists():
        return {}
    college_df = pd.read_csv(COLLEGE_FILE, low_memory=False)
    result = {}
    for _, row in college_df.iterrows():
        player_id = row.get("playerID")
        school_id = row.get("schoolID")
        if not player_id or not school_id or player_id in result:
            continue
        if school_id in school_geo:
            geo = school_geo[school_id]
            result[player_id] = {"lat": geo["lat"], "lon": geo["lon"], "school": geo.get("name")}
    return result


def build_team_year_index(appearances_df: pd.DataFrame, teams_df: pd.DataFrame):
    team_info = {}
    for _, row in teams_df.iterrows():
        tid = row.get("teamID")
        fid = row.get("franchID") or tid
        name = row.get("name", "")
        year = row.get("yearID")
        if tid:
            team_info[tid] = {"franchID": fid, "name": name, "yearID": year}

    index = {}
    for _, row in tqdm(appearances_df.iterrows(), total=len(appearances_df), desc="Building team-year index"):
        player_id = row.get("playerID")
        team_id = row.get("teamID")
        year = row.get("yearID")
        if not player_id or not team_id or not year:
            continue
        info = team_info.get(team_id, {})
        franch_id = info.get("franchID", team_id)
        year_str = str(int(year))
        if franch_id not in index:
            index[franch_id] = {}
        if year_str not in index[franch_id]:
            index[franch_id][year_str] = []
        index[franch_id][year_str].append(player_id)

    return index, team_info


def build_meta(appearances_df: pd.DataFrame, teams_df: pd.DataFrame) -> dict:
    merged = appearances_df.merge(
        teams_df[["teamID", "yearID", "franchID", "name"]].drop_duplicates(),
        on=["teamID", "yearID"],
        how="left",
    )
    franchises = {}
    for _, row in merged.iterrows():
        fid = row.get("franchID") or row.get("teamID")
        year = row.get("yearID")
        name = row.get("name", "")
        if not fid or not year:
            continue
        if fid not in franchises:
            franchises[fid] = {"id": fid, "name": name, "minYear": int(year), "maxYear": int(year)}
        else:
            franchises[fid]["minYear"] = min(franchises[fid]["minYear"], int(year))
            franchises[fid]["maxYear"] = max(franchises[fid]["maxYear"], int(year))
            if name:
                franchises[fid]["name"] = name

    global_min = min(f["minYear"] for f in franchises.values()) if franchises else 1871
    global_max = max(f["maxYear"] for f in franchises.values()) if franchises else 2025

    return {
        "globalMinYear": global_min,
        "globalMaxYear": global_max,
        "franchises": sorted(franchises.values(), key=lambda f: f["name"]),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading CSVs...")
    people_df = pd.read_csv(PEOPLE_FILE, low_memory=False)
    appearances_df = pd.read_csv(APPEARANCES_FILE, low_memory=False)
    teams_df = pd.read_csv(TEAMS_FILE, low_memory=False)

    print("Loading geocoded locations...")
    geocoded = load_geocoded()

    print("Loading high school data...")
    if HIGHSCHOOL_FILE.exists():
        with open(HIGHSCHOOL_FILE) as f:
            hs_geo = json.load(f)
    else:
        hs_geo = {}

    print("Building school/college geo lookups...")
    school_geo = build_school_geo(geocoded)
    college_map = build_college_map(school_geo)

    print("Building team-year index...")
    team_year_index, team_info = build_team_year_index(appearances_df, teams_df)

    # Build per-player team list
    player_teams: dict = {}
    for _, row in appearances_df.iterrows():
        player_id = row.get("playerID")
        team_id = row.get("teamID")
        year = row.get("yearID")
        if not player_id or not team_id or not year:
            continue
        info = team_info.get(team_id, {})
        entry = {
            "year": int(year),
            "teamID": team_id,
            "franchID": info.get("franchID", team_id),
            "name": info.get("name", ""),
        }
        if player_id not in player_teams:
            player_teams[player_id] = []
        player_teams[player_id].append(entry)

    print("Building players.json...")
    players = []
    for _, row in tqdm(people_df.iterrows(), total=len(people_df), desc="Players"):
        pid = row.get("playerID")
        if not pid:
            continue

        first = str(row.get("nameFirst", "") or "").strip()
        last = str(row.get("nameLast", "") or "").strip()
        name = f"{first} {last}".strip() or pid

        debut_raw = str(row.get("debut", "") or "")
        final_raw = str(row.get("finalGame", "") or "")
        debut = int(debut_raw[:4]) if len(debut_raw) >= 4 and debut_raw[:4].isdigit() else None
        final_game = int(final_raw[:4]) if len(final_raw) >= 4 and final_raw[:4].isdigit() else None

        birth_city = str(row.get("birthCity", "") or "").strip()
        birth_state = str(row.get("birthState", "") or "").strip()
        birth_country = str(row.get("birthCountry", "") or "").strip()
        birth_geo = lookup_geo(birth_city, birth_state, birth_country, geocoded)
        birth = {
            "lat": birth_geo["lat"] if birth_geo else None,
            "lon": birth_geo["lon"] if birth_geo else None,
            "city": birth_city or None,
            "state": birth_state or None,
            "country": birth_country or None,
        }

        death_city = str(row.get("deathCity", "") or "").strip()
        death_state = str(row.get("deathState", "") or "").strip()
        death_country = str(row.get("deathCountry", "") or "").strip()
        death_geo = lookup_geo(death_city, death_state, death_country, geocoded)
        death = {
            "lat": death_geo["lat"] if death_geo else None,
            "lon": death_geo["lon"] if death_geo else None,
            "city": death_city or None,
            "state": death_state or None,
            "country": death_country or None,
        } if death_city else None

        col = college_map.get(pid)
        college = {"lat": col["lat"], "lon": col["lon"], "school": col.get("school")} if col else None

        hs = hs_geo.get(pid)
        high_school = {
            "lat": hs["lat"],
            "lon": hs["lon"],
            "school": hs.get("school"),
            "confidence": hs.get("confidence", "high"),
        } if hs else None

        players.append({
            "id": pid,
            "name": name,
            "debut": debut,
            "finalGame": final_game,
            "birth": birth,
            "death": death,
            "college": college,
            "highSchool": high_school,
            "teams": player_teams.get(pid, []),
        })

    players_out = OUTPUT_DIR / "players.json"
    with open(players_out, "w") as f:
        json.dump(players, f, separators=(",", ":"))
    print(f"Wrote {len(players):,} players to {players_out} ({players_out.stat().st_size / 1e6:.1f} MB)")

    index_out = OUTPUT_DIR / "team_year_index.json"
    with open(index_out, "w") as f:
        json.dump(team_year_index, f, separators=(",", ":"))
    print(f"Wrote team_year_index.json ({index_out.stat().st_size / 1e6:.1f} MB)")

    meta = build_meta(appearances_df, teams_df)
    meta_out = OUTPUT_DIR / "meta.json"
    with open(meta_out, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote meta.json ({len(meta['franchises'])} franchises, years {meta['globalMinYear']}-{meta['globalMaxYear']})")

    pop_points = build_population_points(GEONAMES_FILE)
    pop_out = OUTPUT_DIR / "population_points.json"
    with open(pop_out, "w") as f:
        json.dump(pop_points, f, separators=(",", ":"))
    print(f"Wrote population_points.json ({pop_out.stat().st_size / 1e6:.1f} MB)")

    print("\nDone! All data files written to public/data/")


if __name__ == "__main__":
    main()
