import { MOCK_POTHOLES } from '../data/mockPotholes';
import { haversineDistanceMeters } from '../utils/geo';
import type {
  FeedbackType,
  Pothole,
  PotholeFeedbackResult,
  PotholeQueryParams,
} from '../types/pothole';
import type { PotholeService } from './types';

const SIMULATED_LATENCY_MS = 400;
const feedbackCounts = new Map<string, { falsePositive: number; repaired: number }>();
const hiddenPotholes = new Set<string>();

/** Sirve los datos de ejemplo, simulando una llamada de red real. */
export class MockPotholeService implements PotholeService {
  private withCounts() {
    return MOCK_POTHOLES.map((pothole) => {
      const counts = feedbackCounts.get(pothole.id);
      return {
        ...pothole,
        falsePositiveReports: counts?.falsePositive ?? pothole.falsePositiveReports ?? 0,
        repairedReports: counts?.repaired ?? pothole.repairedReports ?? 0,
      };
    });
  }

  async getPotholes(params: PotholeQueryParams = {}): Promise<Pothole[]> {
    await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));

    let result = this.withCounts();
    result = result.filter((pothole) => !hiddenPotholes.has(pothole.id));

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

  async getVotedPotholes(): Promise<Pothole[]> {
    await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));
    return this.withCounts().filter(
      (pothole) => (pothole.falsePositiveReports ?? 0) + (pothole.repairedReports ?? 0) > 0,
    );
  }

  async submitFeedback(id: string, type: FeedbackType): Promise<PotholeFeedbackResult> {
    await new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS));
    const counts = feedbackCounts.get(id) ?? { falsePositive: 0, repaired: 0 };
    if (type === 'false_positive') counts.falsePositive += 1;
    else counts.repaired += 1;
    feedbackCounts.set(id, counts);
    const isVisible = counts.falsePositive < 3 && counts.repaired === 0;
    if (!isVisible) hiddenPotholes.add(id);
    return {
      created: true,
      false_positive_reports: counts.falsePositive,
      repaired_reports: counts.repaired,
      is_visible: isVisible,
    };
  }
}
