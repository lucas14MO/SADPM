interface HeaderProps {
  visibleCount: number;
  isLoading: boolean;
}

export default function Header({ visibleCount, isLoading }: HeaderProps) {
  return (
    <header className="z-20 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">SAD Pothole Map</h1>
        <p className="text-xs text-slate-500 sm:text-sm">Estado de la calzada en Encarnación</p>
      </div>
      <div className="rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white sm:text-sm">
        {isLoading ? 'Cargando…' : `${visibleCount} baches visibles`}
      </div>
    </header>
  );
}
