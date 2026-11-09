import type { Severity } from '../types/pothole';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

interface ApiObservation {
  id: number;
  session_key: string;
  track_id: number;
  severity: Severity;
  human_severity: Severity | null;
  area_norm: number;
  confidence_avg: number;
  frames_detected: number;
  timestamp: string;
  evidence_image: string;
  classified_by_username: string | null;
  classified_at: string | null;
}

export interface CalibrationObservation {
  id: number;
  sessionKey: string;
  trackId: number;
  calculatedSeverity: Severity;
  humanSeverity: Severity | null;
  areaNorm: number;
  confidence: number;
  framesDetected: number;
  timestamp: string;
  imageUrl: string;
  classifiedBy: string | null;
  classifiedAt: string | null;
}

export class CalibrationAccessError extends Error {}

function fromApi(item: ApiObservation): CalibrationObservation {
  return {
    id: item.id,
    sessionKey: item.session_key,
    trackId: item.track_id,
    calculatedSeverity: item.severity,
    humanSeverity: item.human_severity,
    areaNorm: item.area_norm,
    confidence: item.confidence_avg,
    framesDetected: item.frames_detected,
    timestamp: item.timestamp,
    imageUrl: item.evidence_image,
    classifiedBy: item.classified_by_username,
    classifiedAt: item.classified_at,
  };
}

function csrfToken(): string {
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

async function checkResponse(response: Response): Promise<void> {
  if (response.status === 401 || response.status === 403) {
    throw new CalibrationAccessError('Ingresá con una cuenta staff para clasificar observaciones.');
  }
  if (!response.ok) throw new Error(`Error del servidor: ${response.status}`);
}

export async function getCalibrationObservations(): Promise<CalibrationObservation[]> {
  const response = await fetch(`${API_BASE_URL}/observaciones/clasificacion/`, {
    credentials: 'include',
  });
  await checkResponse(response);
  const data: ApiObservation[] = await response.json();
  return data.map(fromApi);
}

export async function classifyObservation(
  id: number,
  humanSeverity: Severity,
): Promise<CalibrationObservation> {
  const response = await fetch(`${API_BASE_URL}/observaciones/clasificacion/${id}/`, {
    method: 'PATCH',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken(),
    },
    body: JSON.stringify({ human_severity: humanSeverity }),
  });
  await checkResponse(response);
  return fromApi(await response.json());
}