import { MockPotholeService } from './mockPotholeService';
import { ApiPotholeService } from './apiPotholeService';
import type { PotholeService } from './types';

export type { PotholeService } from './types';

const useMockData = import.meta.env.VITE_USE_MOCK_DATA !== 'false';

/**
 * Único punto de acceso a los datos de baches para toda la UI.
 * Cambiar de mock a API real es un flag de entorno, no un cambio de estructura.
 */
export const potholeService: PotholeService = useMockData
  ? new MockPotholeService()
  : new ApiPotholeService();
