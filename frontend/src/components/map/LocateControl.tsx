import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import L from 'leaflet';
import { useMap } from 'react-leaflet';

type LocateStatus = 'idle' | 'locating' | 'error';

/** Botón flotente sobre el mapa que centra la vista en la ubicación del usuario. */
export default function LocateControl() {
  const map = useMap();
  const [container, setContainer] = useState<HTMLElement | null>(null);
  const [status, setStatus] = useState<LocateStatus>('idle');
  const markerRef = useRef<L.CircleMarker | null>(null);

  useEffect(() => {
    const control = new L.Control({ position: 'topright' });
    control.onAdd = () => {
      const div = L.DomUtil.create('div');
      L.DomEvent.disableClickPropagation(div);
      L.DomEvent.disableScrollPropagation(div);
      setContainer(div);
      return div;
    };
    control.addTo(map);

    return () => {
      control.remove();
    };
  }, [map]);

  const handleLocate = () => {
    if (!navigator.geolocation) {
      setStatus('error');
      return;
    }

    setStatus('locating');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        map.flyTo([latitude, longitude], 16);

        markerRef.current?.remove();
        markerRef.current = L.circleMarker([latitude, longitude], {
          radius: 8,
          color: '#2563eb',
          weight: 2,
          fillColor: '#3b82f6',
          fillOpacity: 0.9,
        })
          .addTo(map)
          .bindTooltip('Tu ubicación');

        setStatus('idle');
      },
      () => setStatus('error'),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  if (!container) return null;

  return createPortal(
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleLocate}
        title="Ir a mi ubicación"
        aria-label="Ir a mi ubicación"
        className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-lg shadow-md transition hover:bg-slate-50 active:scale-95"
      >
        {status === 'locating' ? '…' : '📍'}
      </button>
      {status === 'error' && (
        <span className="max-w-[10rem] rounded-md bg-red-50 px-2 py-1 text-[11px] text-red-600 shadow">
          No se pudo obtener tu ubicación
        </span>
      )}
    </div>,
    container,
  );
}
