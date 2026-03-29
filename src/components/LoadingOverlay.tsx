import { useDataStore } from '../store/dataStore';

export function LoadingOverlay() {
  const { loaded, error } = useDataStore();

  if (loaded && !error) return null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-900">
      {error ? (
        <div className="text-center">
          <p className="text-red-400 font-semibold mb-2">Failed to load data</p>
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-slate-500 text-xs mt-3">
            Run the pipeline first: <code className="bg-slate-800 px-1 rounded">bash pipeline/01_download.sh</code>
          </p>
        </div>
      ) : (
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-300 text-sm">Loading baseball data…</p>
        </div>
      )}
    </div>
  );
}
