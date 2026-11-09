import { useEffect, useMemo, useState } from 'react';
import { potholeService } from '../services';
import type { Pothole, SearchArea, Severity } from '../types/pothole';

interface UsePotholesResult {
  potholes: Pothole[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

interface LoadResult {
  key: string;
  data: Pothole[];
  error: string | null;
}

/**
 * Carga los baches (todos o los de `searchArea`, filtrados por el backend) y
 * filtra por gravedad en el cliente. Se vuelve a consultar al cambiar el área
 * o al llamar a `reload`.
 */
export function usePotholes(
  activeSeverities: Severity[],
  searchArea: SearchArea | null,
): UsePotholesResult {
  const [reloadToken, setReloadToken] = useState(0);
  const [result, setResult] = useState<LoadResult>({ key: '', data: [], error: null });

  const requestKey = JSON.stringify([
    reloadToken,
    searchArea?.lat,
    searchArea?.lng,
    searchArea?.radiusMeters,
  ]);

  useEffect(() => {
    let cancelled = false;
    const params = searchArea
      ? { lat: searchArea.lat, lng: searchArea.lng, radiusMeters: searchArea.radiusMeters }
      : {};

    potholeService
      .getPotholes(params)
      .then((data) => {
        if (!cancelled) setResult({ key: requestKey, data, error: null });
      })
      .catch(() => {
        if (!cancelled) {
          setResult((previous) => ({
            key: requestKey,
            data: previous.data,
            error: 'No se pudieron cargar los baches. Intentá de nuevo.',
          }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [requestKey, searchArea]);

  // Mientras llega la respuesta se siguen mostrando los datos anteriores.
  const isLoading = result.key !== requestKey;

  const filtered = useMemo(
    () => result.data.filter((pothole) => activeSeverities.includes(pothole.severity)),
    [result.data, activeSeverities],
  );

  return {
    potholes: filtered,
    isLoading,
    error: isLoading ? null : result.error,
    reload: () => setReloadToken((token) => token + 1),
  };
}
