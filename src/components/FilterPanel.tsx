import { useCallback } from 'react';
import { useDataStore } from '../store/dataStore';
import { useFilterStore } from '../store/filterStore';

export function FilterPanel() {
  const { meta } = useDataStore();
  const { yearRange, franchId, setYearRange, setFranchId } = useFilterStore();

  const handleMinYear = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10);
      setYearRange([Math.min(val, yearRange[1]), yearRange[1]]);
    },
    [yearRange, setYearRange]
  );

  const handleMaxYear = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = parseInt(e.target.value, 10);
      setYearRange([yearRange[0], Math.max(val, yearRange[0])]);
    },
    [yearRange, setYearRange]
  );

  if (!meta) return null;

  const { globalMinYear, globalMaxYear, franchises } = meta;

  return (
    <div className="flex flex-col gap-3">
      {/* Year range */}
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1 uppercase tracking-wide">
          Year Range
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 w-10 text-right">{yearRange[0]}</span>
          <div className="flex-1 flex flex-col gap-1">
            <input
              type="range"
              min={globalMinYear}
              max={globalMaxYear}
              value={yearRange[0]}
              onChange={handleMinYear}
              className="w-full accent-sky-400 cursor-pointer"
            />
            <input
              type="range"
              min={globalMinYear}
              max={globalMaxYear}
              value={yearRange[1]}
              onChange={handleMaxYear}
              className="w-full accent-sky-400 cursor-pointer"
            />
          </div>
          <span className="text-xs text-slate-400 w-10">{yearRange[1]}</span>
        </div>
      </div>

      {/* Franchise filter */}
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1 uppercase tracking-wide">
          Franchise
        </label>
        <select
          value={franchId ?? ''}
          onChange={(e) => setFranchId(e.target.value || null)}
          className="w-full bg-slate-700 text-slate-100 text-sm rounded px-2 py-1.5 border border-slate-600 focus:outline-none focus:border-sky-400"
        >
          <option value="">All franchises</option>
          {franchises.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
