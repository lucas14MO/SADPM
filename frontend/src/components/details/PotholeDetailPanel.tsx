import { useEffect, useState } from 'react';
import { SEVERITY_META, formatConfidence, formatDate } from '../../utils/severity';
import type { FeedbackType, Pothole } from '../../types/pothole';

interface PotholeDetailPanelProps {
  pothole: Pothole;
  onClose: () => void;
  onFeedback: (type: FeedbackType) => Promise<void>;
}

export default function PotholeDetailPanel({ pothole, onClose, onFeedback }: PotholeDetailPanelProps) {
  const meta = SEVERITY_META[pothole.severity];
  const totalVotes = (pothole.falsePositiveReports ?? 0) + (pothole.repairedReports ?? 0);
  const isVisible = pothole.isVisible !== false;
  const [submitting, setSubmitting] = useState<FeedbackType | null>(null);
  const [submitted, setSubmitted] = useState<FeedbackType[]>([]);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);
  const [imageExpanded, setImageExpanded] = useState(false);

  useEffect(() => {
    if (!imageExpanded) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setImageExpanded(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [imageExpanded]);

  async function sendFeedback(type: FeedbackType) {
    setSubmitting(type);
    setFeedbackError(null);
    setFeedbackNotice(null);
    try {
      await onFeedback(type);
      setSubmitted((current) => [...current, type]);
      setFeedbackNotice('Reporte recibido. Gracias por validar este bache.');
    } catch {
      setFeedbackError('No se pudo enviar el reporte. Intentá nuevamente.');
    } finally {
      setSubmitting(null);
    }
  }

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

      <div className="mb-3 flex h-44 items-center justify-center overflow-hidden rounded-lg bg-slate-100 text-slate-400">
        {pothole.imageUrl ? (
          <button
            type="button"
            onClick={() => setImageExpanded(true)}
            aria-label="Ampliar imagen de evidencia"
            className="flex h-full w-full cursor-zoom-in items-center justify-center"
          >
            <img
              src={pothole.imageUrl}
              alt="Evidencia del bache con caja de detección"
              className="max-h-full max-w-full object-contain"
            />
          </button>
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

      <div className="mt-4 border-t border-slate-200 pt-3">
        <p className="mb-2 text-xs font-semibold uppercase text-slate-500">Validación ciudadana</p>
        <p className="mb-2 text-xs text-slate-600">Votos totales: {totalVotes}</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            disabled={!isVisible || submitting !== null || submitted.includes('false_positive')}
            onClick={() => void sendFeedback('false_positive')}
            className="min-h-10 rounded-md border border-slate-300 px-2 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting === 'false_positive' ? 'Enviando...' : 'Falso positivo'}
            {pothole.falsePositiveReports ? ` (${pothole.falsePositiveReports})` : ''}
          </button>
          <button
            type="button"
            disabled={!isVisible || submitting !== null || submitted.includes('repaired')}
            onClick={() => void sendFeedback('repaired')}
            className="min-h-10 rounded-md border border-slate-300 px-2 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting === 'repaired' ? 'Enviando...' : 'Ya fue reparado'}
            {pothole.repairedReports ? ` (${pothole.repairedReports})` : ''}
          </button>
        </div>
        {feedbackError && <p role="alert" className="mt-2 text-xs text-red-700">{feedbackError}</p>}
        {feedbackNotice && <p role="status" className="mt-2 text-xs text-green-700">{feedbackNotice}</p>}
      </div>

      {imageExpanded && pothole.imageUrl && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Imagen completa de evidencia"
          onClick={() => setImageExpanded(false)}
          className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/90 p-4"
        >
          <button
            type="button"
            onClick={() => setImageExpanded(false)}
            aria-label="Cerrar imagen ampliada"
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-2xl text-white hover:bg-white/20"
          >
            ×
          </button>
          <img
            src={pothole.imageUrl}
            alt="Evidencia completa del bache con caja de detección"
            onClick={(event) => event.stopPropagation()}
            className="max-h-[92vh] max-w-[96vw] object-contain"
          />
        </div>
      )}
    </div>
  );
}
