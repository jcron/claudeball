import { useDataLoader } from './hooks/useDataLoader';
import { MapView } from './components/MapView';
import { FilterPanel } from './components/FilterPanel';
import { LayerToggle } from './components/LayerToggle';
import { InfoBar } from './components/InfoBar';
import { LoadingOverlay } from './components/LoadingOverlay';

export default function App() {
  useDataLoader();

  return (
    <div className="relative w-full h-full bg-slate-900">
      {/* Full-screen map */}
      <MapView />

      {/* Loading / error overlay */}
      <LoadingOverlay />

      {/* Controls panel — bottom-left */}
      <div className="absolute bottom-6 left-4 z-10 w-72 bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-xl shadow-2xl p-4 flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚾</span>
          <h1 className="text-white font-bold text-base tracking-tight">ClaudeBall</h1>
        </div>

        <FilterPanel />

        <div className="border-t border-slate-700 pt-3">
          <LayerToggle />
        </div>
      </div>

      {/* Info bar — top-right */}
      <div className="absolute top-4 right-4 z-10 bg-slate-800/80 backdrop-blur-sm border border-slate-700 rounded-lg px-3 py-2 max-w-lg">
        <InfoBar />
      </div>
    </div>
  );
}
