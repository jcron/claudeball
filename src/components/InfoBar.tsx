import { useFilteredPoints } from '../hooks/useFilteredPoints';
import { useFilterStore } from '../store/filterStore';
import { useDataStore } from '../store/dataStore';

export function InfoBar() {
  const { matchCount } = useFilteredPoints();
  const { yearRange, franchId } = useFilterStore();
  const { meta } = useDataStore();

  const franchName = meta?.franchises.find((f) => f.id === franchId)?.name;

  return (
    <div className="flex items-center justify-between gap-4 text-xs text-slate-400">
      <div>
        <span className="text-white font-semibold">{matchCount.toLocaleString()}</span>{' '}
        players
        {franchName ? ` · ${franchName}` : ''}
        {' · '}
        {yearRange[0]}–{yearRange[1]}
      </div>
      <div className="text-slate-500">
        Data:{' '}
        <a
          href="https://github.com/cbwinslow/baseballdatabank"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-slate-300"
        >
          Baseball Databank
        </a>{' '}
        (CC BY-SA 3.0) ·{' '}
        <a
          href="https://www.geonames.org/"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-slate-300"
        >
          GeoNames
        </a>{' '}
        (CC BY 4.0)
      </div>
    </div>
  );
}
