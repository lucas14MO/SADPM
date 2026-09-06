import type { Severity } from '../types/pothole';

export const SEVERITY_ORDER: Severity[] = ['leve', 'moderado', 'critico'];

export const SEVERITY_META: Record<Severity, { label: string; color: string; radius: number }> = {
  leve: { label: 'Leve', color: '#22c55e', radius: 7 },
  moderado: { label: 'Moderado', color: '#eab308', radius: 9 },
  critico: { label: 'Crítico', color: '#ef4444', radius: 11 },
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-PY', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}
