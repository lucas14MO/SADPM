import type {
  FeedbackType,
  Pothole,
  PotholeFeedbackResult,
  PotholeQueryParams,
  Severity,
} from '../types/pothole';
import type { PotholeService } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

interface ApiPothole {
  id: number;
  gravedad: Severity;
  latitud: number;
  longitud: number;
  confianza: number;
  area_norm: number | null;
  timestamp_deteccion: string;
  url_imagen: string | null;
  false_positive_reports: number;
  repaired_reports: number;
  is_visible: boolean;
}

function clientToken(): string {
  const key = 'spm-feedback-client-token';
  let token = localStorage.getItem(key);
  if (!token) {
    token = crypto.randomUUID();
    localStorage.setItem(key, token);
  }
  return token;
}

/**
 * Implementación real, lista para conectar con el backend Django + PostGIS (Fase 7).
 * Se activa poniendo VITE_USE_MOCK_DATA=false y VITE_API_BASE_URL en .env.
 * Espera un endpoint del estilo /api/baches/?lat=...&lng=...&radio=...
 */
export class ApiPotholeService implements PotholeService {
  private mapPothole(item: ApiPothole): Pothole {
    return {
      id: String(item.id),
      lat: item.latitud,
      lng: item.longitud,
      severity: item.gravedad,
      confidence: item.confianza,
      detectedAt: item.timestamp_deteccion,
      imageUrl: item.url_imagen ?? undefined,
      areaNorm: item.area_norm ?? undefined,
      falsePositiveReports: item.false_positive_reports,
      repairedReports: item.repaired_reports,
      isVisible: item.is_visible,
    };
  }

  async getPotholes(params: PotholeQueryParams = {}): Promise<Pothole[]> {
    const query = new URLSearchParams();
    if (params.lat !== undefined) query.set('lat', String(params.lat));
    if (params.lng !== undefined) query.set('lng', String(params.lng));
    if (params.radiusMeters !== undefined) query.set('radio', String(params.radiusMeters));
    if (params.severities && params.severities.length > 0) {
      query.set('gravedad', params.severities.join(','));
    }

    const response = await fetch(`${API_BASE_URL}/baches/?${query.toString()}`);
    if (!response.ok) {
      throw new Error(`Error al consultar baches: ${response.status}`);
    }
    const data: ApiPothole[] = await response.json();
    return data.map((item) => this.mapPothole(item));
  }

  async getVotedPotholes(): Promise<Pothole[]> {
    const response = await fetch(`${API_BASE_URL}/baches/votados/`);
    if (!response.ok) throw new Error(`Error al consultar baches votados: ${response.status}`);
    const data: ApiPothole[] = await response.json();
    return data.map((item) => this.mapPothole(item));
  }

  async submitFeedback(id: string, type: FeedbackType): Promise<PotholeFeedbackResult> {
    const response = await fetch(`${API_BASE_URL}/baches/${id}/feedback/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback_type: type, client_token: clientToken() }),
    });
    if (!response.ok) {
      throw new Error(`Error al enviar el reporte: ${response.status}`);
    }
    return response.json();
  }
}
