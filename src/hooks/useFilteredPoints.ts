import { useMemo } from 'react';
import { useDataStore } from '../store/dataStore';
import { useFilterStore } from '../store/filterStore';
import { getFilteredPlayerIds } from '../utils/filterUtils';
import { buildHeatmapPoints } from '../utils/geoUtils';
import type { WeightedPoint } from '../types/player';

interface FilteredPoints {
  birth: WeightedPoint[];
  death: WeightedPoint[];
  college: WeightedPoint[];
  highSchool: WeightedPoint[];
  matchCount: number;
}

export function useFilteredPoints(): FilteredPoints {
  const { players, playerMap, teamYearIndex } = useDataStore();
  const { yearRange, franchId, activeLayers } = useFilterStore();

  const filteredIds = useMemo(
    () => getFilteredPlayerIds(players, teamYearIndex, yearRange, franchId),
    [players, teamYearIndex, yearRange, franchId]
  );

  const birth = useMemo(
    () => (activeLayers.has('birth') ? buildHeatmapPoints(playerMap, filteredIds, 'birth') : []),
    [playerMap, filteredIds, activeLayers]
  );

  const death = useMemo(
    () => (activeLayers.has('death') ? buildHeatmapPoints(playerMap, filteredIds, 'death') : []),
    [playerMap, filteredIds, activeLayers]
  );

  const college = useMemo(
    () => (activeLayers.has('college') ? buildHeatmapPoints(playerMap, filteredIds, 'college') : []),
    [playerMap, filteredIds, activeLayers]
  );

  const highSchool = useMemo(
    () => (activeLayers.has('highSchool') ? buildHeatmapPoints(playerMap, filteredIds, 'highSchool') : []),
    [playerMap, filteredIds, activeLayers]
  );

  return { birth, death, college, highSchool, matchCount: filteredIds.size };
}
