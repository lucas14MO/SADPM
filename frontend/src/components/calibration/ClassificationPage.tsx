import { useEffect, useState } from 'react';
import {
  CalibrationAccessError,
  classifyObservation,
  getCalibrationObservations,
  type CalibrationObservation,
} from '../../services/calibrationService';
import { SEVERITY_META, SEVERITY_ORDER, formatConfidence, formatDate } from '../../utils/severity';
import type { Severity } from '../../types/pothole';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export default function ClassificationPage() {
  const [observations, setObservations] = useState<CalibrationObservation[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCalibrationObservations()
      .then((items) => {
        if (!cancelled) {
          setObservations(items);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(
            error instanceof CalibrationAccessError
              ? error.message
              : 'No se pudieron cargar las muestras de calibración.',
          );
          setObservations([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const current = observations?.[currentIndex];
  const classifiedCount = observations?.filter((item) => item.humanSeverity !== null).length ?? 0;

  async function saveClassification(severity: Severity) {
    if (!current) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await classifyObservation(current.id, severity);
      setObservations((items) => items?.map((item) => item.id === updated.id ? updated : item) ?? []);
      const nextPending = observations?.findIndex(
        (item, index) => index !== currentIndex && item.humanSeverity === null,
      ) ?? -1;
      if (nextPending >= 0) setCurrentIndex(nextPending);
    } catch (error) {
      setSaveError(
        error instanceof CalibrationAccessError
          ? error.message
          : 'No se pudo guardar la clasificación. Revisá la sesión y volvé a intentar.',
      );
    } finally {
      setSaving(false);
    }
  }

  function exportCsv() {
    if (!observations) return;
    const rows = observations
      .filter((item) => item.humanSeverity !== null)
      .map((item) => [item.id, item.sessionKey, item.trackId, item.areaNorm, item.humanSeverity]);
    const quote = (value: string | number | null) => `"${String(value ?? '').replaceAll('"', '""')}"`;
    const content = [
      ['observation_id', 'session_key', 'track_id', 'area_norm', 'human_severity'],
      ...rows,
    ].map((row) => row.map(quote).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'clasificacion_baches.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  if (observations === null) {
    return <p className="p-8 text-sm text-slate-600">Cargando muestras…</p>;
  }

  if (loadError) {
    return (
      <section className="mx-auto max-w-xl p-6 sm:p-10">
        <h2 className="text-xl font-semibold text-slate-900">Clasificación interna</h2>
        <p role="alert" className="mt-3 text-sm text-rose-700">{loadError}</p>
        <a
          href={`${API_BASE_URL.replace(/\/api\/?$/, '')}/admin/`}
          className="mt-5 inline-flex min-h-10 items-center rounded-md bg-teal-800 px-4 text-sm font-medium text-white hover:bg-teal-900"
        >
          Iniciar sesión en Django
        </a>
        <button
          type="button"
          onClick={() => setReloadToken((token) => token + 1)}
          className="ml-3 min-h-10 rounded-md border border-slate-300 px-4 text-sm text-slate-700 hover:bg-slate-50"
        >
          Reintentar
        </button>
      </section>
    );
  }

  return (
    <main className="h-full overflow-y-auto bg-slate-100 p-4 sm:p-6">
      <div className="mx-auto max-w-6xl">
        <header className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-slate-300 pb-4">
          <div>
            <p className="text-xs font-semibold uppercase text-teal-800">Calibración</p>
            <h2 className="mt-1 text-xl font-semibold text-slate-900">Clasificar recortes</h2>
            <p className="mt-1 text-sm text-slate-600">
              {classifiedCount} de {observations.length} muestras clasificadas
            </p>
          </div>
          <button
            type="button"
            onClick={exportCsv}
            disabled={classifiedCount === 0}
            className="min-h-10 rounded-md border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Descargar CSV
          </button>
        </header>

        {!current ? (
          <p className="py-10 text-center text-sm text-slate-600">
            {observations.length === 0 ? 'No hay recortes con area_norm para clasificar.' : 'No quedan muestras pendientes.'}
          </p>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="flex min-h-[50vh] items-center justify-center rounded-lg border border-slate-300 bg-slate-950 p-3">
              <img
                src={current.imageUrl}
                alt={`Recorte de bache ${current.trackId}`}
                className="max-h-[70vh] max-w-full object-contain"
              />
            </div>

            <aside className="flex flex-col gap-5 border-t border-slate-300 pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-slate-700">Muestra {currentIndex + 1} / {observations.length}</span>
                <span className="text-slate-500">#{current.id}</span>
              </div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
                <dt className="text-slate-500">area_norm</dt>
                <dd className="text-right font-mono tabular-nums text-slate-900">{current.areaNorm.toFixed(8)}</dd>
                <dt className="text-slate-500">Clase calculada</dt>
                <dd className="text-right text-slate-900">{SEVERITY_META[current.calculatedSeverity].label}</dd>
                <dt className="text-slate-500">Confianza</dt>
                <dd className="text-right text-slate-900">{formatConfidence(current.confidence)}</dd>
                <dt className="text-slate-500">Frames</dt>
                <dd className="text-right text-slate-900">{current.framesDetected}</dd>
                <dt className="text-slate-500">Sesión / track</dt>
                <dd className="break-all text-right text-xs text-slate-900">{current.sessionKey} / {current.trackId}</dd>
                <dt className="text-slate-500">Fecha</dt>
                <dd className="text-right text-slate-900">{formatDate(current.timestamp)}</dd>
                <dt className="text-slate-500">Etiqueta humana</dt>
                <dd className="text-right font-medium text-slate-900">
                  {current.humanSeverity ? SEVERITY_META[current.humanSeverity].label : 'Pendiente'}
                </dd>
              </dl>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Clasificación humana</p>
                <div className="grid grid-cols-3 gap-2">
                  {SEVERITY_ORDER.map((severity) => {
                    const meta = SEVERITY_META[severity];
                    return (
                      <button
                        key={severity}
                        type="button"
                        disabled={saving}
                        onClick={() => void saveClassification(severity)}
                        className="min-h-11 rounded-md px-2 text-sm font-semibold text-white disabled:opacity-50"
                        style={{ backgroundColor: meta.color }}
                      >
                        {meta.label}
                      </button>
                    );
                  })}
                </div>
                {saving && <p role="status" className="mt-2 text-xs text-slate-600">Guardando…</p>}
                {saveError && <p role="alert" className="mt-2 text-xs text-rose-700">{saveError}</p>}
              </div>

              <nav className="mt-auto flex justify-between border-t border-slate-200 pt-3">
                <button
                  type="button"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((index) => Math.max(0, index - 1))}
                  className="min-h-10 rounded-md border border-slate-300 px-3 text-sm text-slate-700 disabled:opacity-40"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  disabled={currentIndex >= observations.length - 1}
                  onClick={() => setCurrentIndex((index) => Math.min(observations.length - 1, index + 1))}
                  className="min-h-10 rounded-md border border-slate-300 px-3 text-sm text-slate-700 disabled:opacity-40"
                >
                  Siguiente
                </button>
              </nav>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}