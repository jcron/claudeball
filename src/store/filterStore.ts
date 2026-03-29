import { create } from 'zustand';
import type { LayerKey } from '../types/player';

interface FilterState {
  yearRange: [number, number];
  franchId: string | null;
  activeLayers: Set<LayerKey>;
  setYearRange: (range: [number, number]) => void;
  setFranchId: (id: string | null) => void;
  toggleLayer: (layer: LayerKey) => void;
  setActiveLayers: (layers: Set<LayerKey>) => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  yearRange: [1871, 2025],
  franchId: null,
  activeLayers: new Set<LayerKey>(['birth']),
  setYearRange: (range) => set({ yearRange: range }),
  setFranchId: (franchId) => set({ franchId }),
  toggleLayer: (layer) =>
    set((state) => {
      const next = new Set(state.activeLayers);
      if (next.has(layer)) {
        next.delete(layer);
      } else {
        next.add(layer);
      }
      return { activeLayers: next };
    }),
  setActiveLayers: (activeLayers) => set({ activeLayers }),
}));
