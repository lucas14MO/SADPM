export type Severity = 'leve' | 'moderado' | 'critico';

export interface Pothole {
  id: string;
  lat: number;
  lng: number;
  severity: Severity;
  /** 0..1 */
  confidence: number;
  /** ISO 8601 */
  detectedAt: string;
  address?: string;
  imageUrl?: string;
}

/** Mirrors the query shape the future Django/PostGIS API is expected to expose (Fase 7). */
export interface PotholeQueryParams {
  lat?: number;
  lng?: number;
  radiusMeters?: number;
  severities?: Severity[];
}
