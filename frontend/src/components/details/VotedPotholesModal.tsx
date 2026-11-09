import { useEffect, useState } from 'react';
import { SEVERITY_META, formatDate } from '../../utils/severity';
import type { Pothole } from '../../types/pothole';
import { potholeService } from '../../services';

interface VotedPotholesModalProps {
  onClose: () => void;
  onSelect: (pothole: Pothole) => void;
}

export default function VotedPotholesModal({ onClose, onSelect }: VotedPotholesModalProps) {
  const [potholes, setPotholes] = useState<Pothole[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    potholeService.getVotedPotholes()
      .then((items) => { if (!cancelled) setPotholes(items); })
      .catch(() => { if (!cancelled) setError('No se pudieron cargar los baches con votos.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      cancelled = true;
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="voted-potholes-title"
      onClick={onClose}
      className="fixed inset-0 z-[1500] flex items-center justify-center bg-slate-950/50 p-4"
    >
      <section
        onClick={(event) => event.stopPropagation()}
        className="flex max-h-[85vh] w-full max-w-xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <h2 id="voted-potholes-title" className="font-semibold text-slate-900">Baches con votos</h2>
            <p className="text-xs text-slate-500">Reportes ciudadanos de falso positivo y reparación</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Cerrar" className="rounded p-2 text-slate-500 hover:bg-slate-100">✕</button>
        </header>
        <div className="overflow-y-auto p-4">
          {loading && <p className="py-8 text-center text-sm text-slate-500">Cargando…</p>}
          {error && <p role="alert" className="py-8 text-center text-sm text-red-700">{error}</p>}
          {!loading && !error && potholes.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500">Todavía no hay reportes ciudadanos.</p>
          )}
          <ul className="space-y-2">
            {potholes.map((pothole) => {
              const severity = SEVERITY_META[pothole.severity];
              const falseVotes = pothole.falsePositiveReports ?? 0;
              const repairedVotes = pothole.repairedReports ?? 0;
              return (
                <li key={pothole.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(pothole)}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 text-left hover:border-slate-400 hover:bg-slate-50"
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-slate-900">Bache #{pothole.id}</span>
                      <span className="block text-xs text-slate-500">{pothole.lat.toFixed(5)}, {pothole.lng.toFixed(5)} · {formatDate(pothole.detectedAt)}</span>
                    </span>
                    <span className="shrink-0 text-right text-xs">
                      <span className="block font-semibold" style={{ color: severity.color }}>{severity.label}</span>
                      <span className="block text-slate-600">Falso positivo: {falseVotes}</span>
                      <span className="block text-slate-600">Reparado: {repairedVotes}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </section>
    </div>
  );
}
