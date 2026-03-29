import type { Player } from '../types/player';

/**
 * Returns the set of playerIDs matching the current filter state.
 *
 * - If franchId is set: union of players who appeared for that franchise in any year in [minYear, maxYear]
 * - If franchId is null: all players whose career (debut–finalGame) overlaps the year range
 */
export function getFilteredPlayerIds(
  players: Player[],
  teamYearIndex: Record<string, Record<string, string[]>>,
  yearRange: [number, number],
  franchId: string | null
): Set<string> {
  const [minYear, maxYear] = yearRange;

  if (franchId) {
    const franchData = teamYearIndex[franchId];
    if (!franchData) return new Set();
    const ids = new Set<string>();
    for (let y = minYear; y <= maxYear; y++) {
      const yearPlayers = franchData[String(y)];
      if (yearPlayers) {
        for (const id of yearPlayers) ids.add(id);
      }
    }
    return ids;
  }

  // No franchise filter — include all players whose career overlaps the range
  const ids = new Set<string>();
  for (const player of players) {
    const debut = player.debut ?? 0;
    const final = player.finalGame ?? 9999;
    if (debut <= maxYear && final >= minYear) {
      ids.add(player.id);
    }
  }
  return ids;
}
