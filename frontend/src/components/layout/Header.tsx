import { formatRadius } from '../../utils/geo';

interface HeaderProps {
  visibleCount: number;
  isLoading: boolean;
  /** Radio de la búsqueda activa, o null si se muestran todos los baches. */
  radiusMeters: number | null;
}

export default function Header({ visibleCount, isLoading, radiusMeters }: HeaderProps) {
  const scope = radiusMeters === null ? '' : ` en ${formatRadius(radiusMeters)}`;

  return (
    <header className="z-20 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 sm:text-xl">SAD Pothole Map</h1>
        <p className="text-xs text-slate-500 sm:text-sm">Estado de la calzada en Encarnación</p>
      </div>
      <div className="rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white sm:text-sm">
        {isLoading ? 'Cargando…' : `${visibleCount} baches visibles${scope}`}
      </div>
    </header>
  );
}
