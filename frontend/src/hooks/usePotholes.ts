import { useEffect, useMemo, useState } from 'react';
import { potholeService } from '../services';
import type { Pothole, Severity } from '../types/pothole';

interface UsePotholesResult {
  potholes: Pothole[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

interface SpatialQuery {
  lat: number;
  lng: number;
  radiusMeters: number;
}

/** Carga los baches del radio seleccionado y filtra por gravedad. */
export function usePotholes(
  activeSeverities: Severity[],
  spatialQuery: SpatialQuery,
): UsePotholesResult {
  const { lat, lng, radiusMeters } = spatialQuery;
  const [potholes, setPotholes] = useState<Pothole[]>([]);
  const [requestError, setRequestError] = useState<{ key: string; message: string } | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [completedRequestKey, setCompletedRequestKey] = useState<string | null>(null);
  const requestKey = JSON.stringify([lat, lng, radiusMeters, activeSeverities, reloadToken]);

  useEffect(() => {
    let cancelled = false;

    potholeService
      .getPotholes({ lat, lng, radiusMeters, severities: activeSeverities })
      .then((data) => {
        if (!cancelled) setPotholes(data);
      })
      .catch(() => {
        if (!cancelled) {
          setRequestError({
            key: requestKey,
            message: 'No se pudieron cargar los baches. Intentá de nuevo.',
          });
        }
      })
      .finally(() => {
        if (!cancelled) setCompletedRequestKey(requestKey);
      });

    return () => {
      cancelled = true;
    };
  }, [lat, lng, radiusMeters, activeSeverities, requestKey]);

  const filtered = useMemo(
    () => potholes.filter((pothole) => activeSeverities.includes(pothole.severity)),
    [potholes, activeSeverities],
  );

  return {
    potholes: filtered,
    isLoading: completedRequestKey !== requestKey,
    error: requestError?.key === requestKey ? requestError.message : null,
    reload: () => setReloadToken((token) => token + 1),
  };
}
