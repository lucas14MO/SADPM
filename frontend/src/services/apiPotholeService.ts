import type { Pothole, PotholeQueryParams } from '../types/pothole';
import type { PotholeService } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

/**
 * Implementación real, lista para conectar con el backend Django + PostGIS (Fase 7).
 * Se activa poniendo VITE_USE_MOCK_DATA=false y VITE_API_BASE_URL en .env.
 * Espera un endpoint del estilo /api/baches/?lat=...&lng=...&radio=...
 */
export class ApiPotholeService implements PotholeService {
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
    return response.json();
  }
}
