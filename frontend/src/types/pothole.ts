export type Severity = 'leve' | 'moderado' | 'critico';
export type FeedbackType = 'false_positive' | 'repaired';

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
  areaNorm?: number;
  falsePositiveReports?: number;
  repairedReports?: number;
  isVisible?: boolean;
}

export interface PotholeFeedbackResult {
  created: boolean;
  false_positive_reports: number;
  repaired_reports: number;
  is_visible: boolean;
}

/** Mirrors the query shape the future Django/PostGIS API is expected to expose (Fase 7). */
export interface PotholeQueryParams {
  lat?: number;
  lng?: number;
  radiusMeters?: number;
  severities?: Severity[];
}
