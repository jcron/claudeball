import type { Player, WeightedPoint } from '../types/player';

type Layer = 'birth' | 'death' | 'college' | 'highSchool';

/**
 * Builds a [lon, lat, 1][] array for the given layer type,
 * filtered to only players in the provided ID set.
 */
export function buildHeatmapPoints(
  playerMap: Map<string, Player>,
  playerIds: Set<string>,
  layer: Layer
): WeightedPoint[] {
  const points: WeightedPoint[] = [];

  for (const id of playerIds) {
    const player = playerMap.get(id);
    if (!player) continue;

    let lat: number | null = null;
    let lon: number | null = null;

    if (layer === 'birth' && player.birth) {
      lat = player.birth.lat;
      lon = player.birth.lon;
    } else if (layer === 'death' && player.death) {
      lat = player.death.lat;
      lon = player.death.lon;
    } else if (layer === 'college' && player.college) {
      lat = player.college.lat;
      lon = player.college.lon;
    } else if (layer === 'highSchool' && player.highSchool) {
      lat = player.highSchool.lat;
      lon = player.highSchool.lon;
    }

    if (lat != null && lon != null && isFinite(lat) && isFinite(lon)) {
      points.push([lon, lat, 1]);
    }
  }

  return points;
}
