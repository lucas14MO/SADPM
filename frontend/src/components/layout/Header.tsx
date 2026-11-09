interface HeaderProps {
  visibleCount: number;
  isLoading: boolean;
  view: 'map' | 'calibration';
  onViewChange: (view: 'map' | 'calibration') => void;
}

export default function Header({ visibleCount, isLoading, view, onViewChange }: HeaderProps) {
  return (
    <header className="z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">SAD Pothole Map</h1>
        <p className="text-xs text-slate-500 sm:text-sm">Estado de la calzada en Encarnación</p>
      </div>
      <nav aria-label="Secciones" className="flex rounded-md border border-slate-200 p-1">
        <button
          type="button"
          aria-pressed={view === 'map'}
          onClick={() => onViewChange('map')}
          className={`rounded px-3 py-1.5 text-sm ${view === 'map' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
        >
          Mapa
        </button>
        <button
          type="button"
          aria-pressed={view === 'calibration'}
          onClick={() => onViewChange('calibration')}
          className={`rounded px-3 py-1.5 text-sm ${view === 'calibration' ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
        >
          Calibración
        </button>
      </nav>
      <div className="rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white sm:text-sm">
        {isLoading ? 'Cargando…' : `${visibleCount} baches visibles`}
      </div>
    </header>
  );
}
