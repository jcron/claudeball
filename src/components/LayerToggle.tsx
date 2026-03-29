import { useFilterStore } from '../store/filterStore';
import type { LayerKey } from '../types/player';

interface LayerConfig {
  key: LayerKey;
  label: string;
  color: string;
  note?: string;
}

const PLAYER_LAYERS: LayerConfig[] = [
  { key: 'birth', label: 'Birthplace', color: 'bg-sky-400' },
  { key: 'death', label: 'Death place', color: 'bg-orange-400' },
  { key: 'college', label: 'College', color: 'bg-green-400' },
  {
    key: 'highSchool',
    label: 'High school',
    color: 'bg-purple-400',
    note: 'Post-1960 players only; ~30–50% coverage',
  },
];

const REFERENCE_LAYERS: LayerConfig[] = [
  {
    key: 'population',
    label: 'World population density',
    color: 'bg-slate-400',
    note: 'Toggle to compare against player density',
  },
];

function LayerRow({ layer }: { layer: LayerConfig }) {
  const { activeLayers, toggleLayer } = useFilterStore();
  const active = activeLayers.has(layer.key);

  return (
    <label className="flex items-start gap-2 cursor-pointer group">
      <div className="relative flex items-center mt-0.5">
        <input
          type="checkbox"
          checked={active}
          onChange={() => toggleLayer(layer.key)}
          className="sr-only"
        />
        <div
          className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
            active ? `${layer.color} border-transparent` : 'bg-transparent border-slate-500'
          }`}
        >
          {active && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2 6l3 3 5-5" />
            </svg>
          )}
        </div>
      </div>
      <div>
        <span className={`text-sm ${active ? 'text-white' : 'text-slate-400'} transition-colors`}>
          {layer.label}
        </span>
        {layer.note && (
          <p className="text-xs text-slate-500 mt-0.5">{layer.note}</p>
        )}
      </div>
    </label>
  );
}

export function LayerToggle() {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
          Player layers
        </p>
        <div className="flex flex-col gap-2">
          {PLAYER_LAYERS.map((l) => (
            <LayerRow key={l.key} layer={l} />
          ))}
        </div>
      </div>

      <div className="border-t border-slate-600 pt-3">
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-2">
          Reference overlay
        </p>
        <div className="flex flex-col gap-2">
          {REFERENCE_LAYERS.map((l) => (
            <LayerRow key={l.key} layer={l} />
          ))}
        </div>
      </div>
    </div>
  );
}
