import { SEVERITY_META, formatConfidence, formatDate } from '../../utils/severity';
import type { Pothole } from '../../types/pothole';

interface PotholeDetailPanelProps {
  pothole: Pothole;
  onClose: () => void;
}

export default function PotholeDetailPanel({ pothole, onClose }: PotholeDetailPanelProps) {
  const meta = SEVERITY_META[pothole.severity];

  return (
    <div className="absolute inset-x-0 bottom-0 z-[1100] max-h-[70vh] overflow-y-auto rounded-t-2xl bg-white p-4 shadow-2xl sm:inset-x-auto sm:bottom-4 sm:right-4 sm:top-20 sm:w-80 sm:rounded-2xl">
      <div className="mb-3 flex items-start justify-between">
        <span
          className="rounded-full px-3 py-1 text-xs font-semibold text-white"
          style={{ backgroundColor: meta.color }}
        >
          {meta.label}
        </span>
        <button
          type="button"
          onClick={onClose}
          aria-label="Cerrar"
          className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          ✕
        </button>
      </div>

      <div className="mb-3 flex h-36 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
        {pothole.imageUrl ? (
          <img
            src={pothole.imageUrl}
            alt="Foto del bache"
            className="h-full w-full rounded-xl object-cover"
          />
        ) : (
          <span className="text-sm">Sin imagen disponible</span>
        )}
      </div>

      <dl className="space-y-2 text-sm text-slate-600">
        <div className="flex justify-between">
          <dt className="font-medium text-slate-500">Confianza de detección</dt>
          <dd>{formatConfidence(pothole.confidence)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="font-medium text-slate-500">Fecha de detección</dt>
          <dd>{formatDate(pothole.detectedAt)}</dd>
        </div>
        {pothole.address && (
          <div className="flex justify-between gap-2">
            <dt className="font-medium text-slate-500">Ubicación</dt>
            <dd className="text-right">{pothole.address}</dd>
          </div>
        )}
        <div className="flex justify-between">
          <dt className="font-medium text-slate-500">Coordenadas</dt>
          <dd>
            {pothole.lat.toFixed(5)}, {pothole.lng.toFixed(5)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
