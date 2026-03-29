import { useEffect } from 'react';
import { useDataStore } from '../store/dataStore';
import { useFilterStore } from '../store/filterStore';
import type { Meta, Player, WeightedPoint } from '../types/player';

const BASE = import.meta.env.BASE_URL;

export function useDataLoader() {
  const { setData, setError, loaded } = useDataStore();
  const setYearRange = useFilterStore((s) => s.setYearRange);

  useEffect(() => {
    if (loaded) return;

    async function load() {
      try {
        const [playersRes, indexRes, metaRes, popRes] = await Promise.all([
          fetch(`${BASE}data/players.json`),
          fetch(`${BASE}data/team_year_index.json`),
          fetch(`${BASE}data/meta.json`),
          fetch(`${BASE}data/population_points.json`),
        ]);

        if (!playersRes.ok || !indexRes.ok || !metaRes.ok || !popRes.ok) {
          throw new Error('Failed to load data files');
        }

        const [players, teamYearIndex, meta, populationPoints]: [
          Player[],
          Record<string, Record<string, string[]>>,
          Meta,
          WeightedPoint[],
        ] = await Promise.all([
          playersRes.json(),
          indexRes.json(),
          metaRes.json(),
          popRes.json(),
        ]);

        setData(players, teamYearIndex, meta, populationPoints);
        setYearRange([meta.globalMinYear, meta.globalMaxYear]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error loading data');
      }
    }

    load();
  }, [loaded, setData, setError, setYearRange]);
}
