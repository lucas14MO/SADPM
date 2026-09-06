import type { Pothole } from '../types/pothole';

/**
 * Datos de ejemplo para desarrollo de la interfaz, sin backend todavía.
 * Coordenadas ilustrativas alrededor del centro de Encarnación, Paraguay.
 * Reemplazar por datos reales de la API cuando esté disponible (ver src/services).
 */
export const MOCK_POTHOLES: Pothole[] = [
  { id: 'p001', lat: -27.3306, lng: -55.8657, severity: 'critico', confidence: 0.94, detectedAt: '2026-08-20T09:12:00Z', address: 'Av. Irrazábal casi Mallorquín' },
  { id: 'p002', lat: -27.3298, lng: -55.8632, severity: 'moderado', confidence: 0.81, detectedAt: '2026-08-21T14:05:00Z', address: 'Av. Irrazábal casi Cabañas' },
  { id: 'p003', lat: -27.3341, lng: -55.8674, severity: 'leve', confidence: 0.68, detectedAt: '2026-08-22T08:47:00Z', address: 'Costanera José Asunción Flores' },
  { id: 'p004', lat: -27.3352, lng: -55.8611, severity: 'critico', confidence: 0.97, detectedAt: '2026-08-18T11:30:00Z', address: 'Av. Casco Boher' },
  { id: 'p005', lat: -27.3275, lng: -55.8598, severity: 'moderado', confidence: 0.76, detectedAt: '2026-08-25T16:20:00Z', address: 'Calle Estigarribia' },
  { id: 'p006', lat: -27.3319, lng: -55.8703, severity: 'leve', confidence: 0.63, detectedAt: '2026-08-27T10:02:00Z', address: 'Calle Mons. Bogarín' },
  { id: 'p007', lat: -27.3389, lng: -55.8642, severity: 'critico', confidence: 0.91, detectedAt: '2026-08-15T07:55:00Z', address: 'Ruta Nacional 1, acceso norte' },
  { id: 'p008', lat: -27.3263, lng: -55.8671, severity: 'moderado', confidence: 0.79, detectedAt: '2026-08-29T13:40:00Z', address: 'Barrio San Isidro' },
  { id: 'p009', lat: -27.3247, lng: -55.8619, severity: 'leve', confidence: 0.71, detectedAt: '2026-08-30T09:15:00Z', address: 'Av. Bernardino Caballero' },
  { id: 'p010', lat: -27.3372, lng: -55.8589, severity: 'critico', confidence: 0.88, detectedAt: '2026-08-19T18:22:00Z', address: 'Calle Pa.i Pérez' },
  { id: 'p011', lat: -27.3308, lng: -55.8564, severity: 'moderado', confidence: 0.74, detectedAt: '2026-09-01T12:10:00Z', address: 'Av. Dr. Francia' },
  { id: 'p012', lat: -27.3355, lng: -55.8733, severity: 'leve', confidence: 0.66, detectedAt: '2026-09-02T15:48:00Z', address: 'Costanera, tramo sur' },
  { id: 'p013', lat: -27.3221, lng: -55.8655, severity: 'moderado', confidence: 0.83, detectedAt: '2026-08-24T09:37:00Z', address: 'Barrio Villa Alta' },
  { id: 'p014', lat: -27.3406, lng: -55.8697, severity: 'critico', confidence: 0.95, detectedAt: '2026-08-17T08:05:00Z', address: 'Acceso Ruta 1, altura Km 2' },
  { id: 'p015', lat: -27.3285, lng: -55.8541, severity: 'leve', confidence: 0.6, detectedAt: '2026-09-03T11:52:00Z', address: 'Barrio Quiromipoty' },
  { id: 'p016', lat: -27.3333, lng: -55.8598, severity: 'moderado', confidence: 0.78, detectedAt: '2026-08-28T17:03:00Z', address: 'Calle 25 de Mayo' },
  { id: 'p017', lat: -27.3259, lng: -55.8712, severity: 'leve', confidence: 0.69, detectedAt: '2026-09-04T09:28:00Z', address: 'Barrio Itá Pyta Punta' },
  { id: 'p018', lat: -27.3378, lng: -55.8617, severity: 'critico', confidence: 0.9, detectedAt: '2026-08-16T13:15:00Z', address: 'Av. Irrazábal casi Tomás Romero Pereira' },
  { id: 'p019', lat: -27.3211, lng: -55.8598, severity: 'moderado', confidence: 0.77, detectedAt: '2026-08-31T10:44:00Z', address: 'Barrio Mboi Ka\'e' },
  { id: 'p020', lat: -27.3296, lng: -55.8686, severity: 'leve', confidence: 0.65, detectedAt: '2026-09-05T14:33:00Z', address: 'Calle Cabañas, tramo centro' },
];
