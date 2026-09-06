import { useEffect, useMemo, useState } from 'react';
import { potholeService } from '../services';
import type { Pothole, Severity } from '../types/pothole';

interface UsePotholesResult {
  potholes: Pothole[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

/** Carga los baches una vez y filtra por gravedad en el cliente. */
export function usePotholes(activeSeverities: Severity[]): UsePotholesResult {
  const [potholes, setPotholes] = useState<Pothole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    potholeService
      .getPotholes()
      .then((data) => {
        if (!cancelled) setPotholes(data);
      })
      .catch(() => {
        if (!cancelled) setError('No se pudieron cargar los baches. Intentá de nuevo.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const filtered = useMemo(
    () => potholes.filter((pothole) => activeSeverities.includes(pothole.severity)),
    [potholes, activeSeverities],
  );

  return {
    potholes: filtered,
    isLoading,
    error,
    reload: () => setReloadToken((token) => token + 1),
  };
}
