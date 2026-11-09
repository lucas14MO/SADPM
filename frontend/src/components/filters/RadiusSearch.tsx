import type { SearchArea } from '../../types/pothole';
import { RADIUS_OPTIONS_METERS, formatRadius } from '../../utils/geo';

interface RadiusSearchProps {
  area: SearchArea | null;
  isPicking: boolean;
  radiusMeters: number;
  onStartPicking: () => void;
  onCancelPicking: () => void;
  onRadiusChange: (radiusMeters: number) => void;
  onClear: () => void;
}

/** Búsqueda de baches alrededor de un punto elegido en el mapa. */
export default function RadiusSearch({
  area,
  isPicking,
  radiusMeters,
  onStartPicking,
  onCancelPicking,
  onRadiusChange,
  onClear,
}: RadiusSearchProps) {
  const buttonBase =
    'rounded-full border px-3 py-1.5 text-xs font-medium transition sm:text-sm';

  return (
    <div className="absolute bottom-6 left-3 z-[1000] max-w-[calc(100%-1.5rem)] rounded-xl bg-white/95 p-2 shadow-md backdrop-blur">
      {isPicking ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-1 text-xs font-medium text-slate-700 sm:text-sm">
            Tocá el mapa para elegir el centro
          </span>
          <button
            type="button"
            onClick={onCancelPicking}
            className={`${buttonBase} border-slate-300 bg-white text-slate-700 hover:bg-slate-50`}
          >
            Cancelar
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onStartPicking}
              className={`${buttonBase} border-transparent bg-slate-900 text-white hover:bg-slate-700`}
            >
              {area ? 'Cambiar punto' : 'Buscar en un radio'}
            </button>
            {area && (
              <button
                type="button"
                onClick={onClear}
                className={`${buttonBase} border-slate-300 bg-white text-slate-700 hover:bg-slate-50`}
              >
                Ver todos
              </button>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Radio de búsqueda">
            <span className="px-1 text-xs text-slate-500">Radio:</span>
            {RADIUS_OPTIONS_METERS.map((option) => {
              const isActive = option === radiusMeters;
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => onRadiusChange(option)}
                  aria-pressed={isActive}
                  className={`rounded-full border px-2.5 py-1 text-xs font-medium transition ${
                    isActive
                      ? 'border-transparent bg-sky-600 text-white'
                      : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {formatRadius(option)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
