import type {
  FeedbackType,
  Pothole,
  PotholeFeedbackResult,
  PotholeQueryParams,
} from '../types/pothole';

/**
 * Contrato que debe cumplir cualquier fuente de datos de baches, sea mock o real.
 * La UI solo depende de esta interfaz, nunca de la implementación concreta.
 */
export interface PotholeService {
  getPotholes(params?: PotholeQueryParams): Promise<Pothole[]>;
  getVotedPotholes(): Promise<Pothole[]>;
  submitFeedback(id: string, type: FeedbackType): Promise<PotholeFeedbackResult>;
}
