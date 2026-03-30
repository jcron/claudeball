export interface GeoPoint {
  lat: number | null;
  lon: number | null;
}

export interface BirthLocation extends GeoPoint {
  city: string | null;
  state: string | null;
  country: string | null;
}

export interface CollegeLocation extends GeoPoint {
  school: string | null;
}

export interface HighSchoolLocation extends GeoPoint {
  school: string | null;
  city: string | null;
  state: string | null;
}

export interface TeamEntry {
  year: number;
  teamID: string;
  franchID: string;
  name: string;
}

export interface Player {
  id: string;
  name: string;
  debut: number | null;
  finalGame: number | null;
  birth: BirthLocation;
  college: CollegeLocation | null;
  highSchool: HighSchoolLocation | null;
  teams: TeamEntry[];
}

export interface Franchise {
  id: string;
  name: string;
  minYear: number;
  maxYear: number;
}

export interface Meta {
  globalMinYear: number;
  globalMaxYear: number;
  franchises: Franchise[];
}

// [lon, lat, weight]
export type WeightedPoint = [number, number, number];

export type LayerKey = 'birth' | 'college' | 'highSchool' | 'population';
