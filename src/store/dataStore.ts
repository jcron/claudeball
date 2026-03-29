import { create } from 'zustand';
import type { Meta, Player, WeightedPoint } from '../types/player';

interface DataState {
  players: Player[];
  playerMap: Map<string, Player>;
  teamYearIndex: Record<string, Record<string, string[]>>;
  meta: Meta | null;
  populationPoints: WeightedPoint[];
  loaded: boolean;
  error: string | null;
  setData: (
    players: Player[],
    teamYearIndex: Record<string, Record<string, string[]>>,
    meta: Meta,
    populationPoints: WeightedPoint[]
  ) => void;
  setError: (error: string) => void;
}

export const useDataStore = create<DataState>((set) => ({
  players: [],
  playerMap: new Map(),
  teamYearIndex: {},
  meta: null,
  populationPoints: [],
  loaded: false,
  error: null,
  setData: (players, teamYearIndex, meta, populationPoints) => {
    const playerMap = new Map(players.map((p) => [p.id, p]));
    set({ players, playerMap, teamYearIndex, meta, populationPoints, loaded: true, error: null });
  },
  setError: (error) => set({ error, loaded: true }),
}));
