import { MOCK_POTHOLES } from '../data/mockPotholes';
import { haversineDistanceMeters } from '../utils/geo';
import type { Pothole, PotholeQueryParams } from '../types/pothole';
import type { PotholeService } from './types';

const SIMULATED_LATENCY_MS = 400;

/** Sirve los datos de ejemplo, simulando una llamada de red real. */
export class MockPotholeService implements PotholeService {
  async getPotholes(params: PotholeQueryParams = {}): Promise<Pothole[]> {
    await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));

    let result = [...MOCK_POTHOLES];

    if (params.severities && params.severities.length > 0) {
      const active = params.severities;
      result = result.filter((pothole) => active.includes(pothole.severity));
    }

    if (params.lat !== undefined && params.lng !== undefined && params.radiusMeters !== undefined) {
      const { lat, lng, radiusMeters } = params;
      result = result.filter(
        (pothole) => haversineDistanceMeters(lat, lng, pothole.lat, pothole.lng) <= radiusMeters,
      );
    }

    return result;
  }
}
