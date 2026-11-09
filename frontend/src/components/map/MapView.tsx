import { useEffect } from 'react';
import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import LocateControl from './LocateControl';
import { SEVERITY_META } from '../../utils/severity';
import type { Pothole, SearchArea } from '../../types/pothole';

const ENCARNACION_CENTER: [number, number] = [-27.3306, -55.8657];
const DEFAULT_ZOOM = 14;

interface MapViewProps {
  potholes: Pothole[];
  selectedId: string | null;
  onSelectPothole: (pothole: Pothole) => void;
  searchArea: SearchArea | null;
  isPickingCenter: boolean;
  onPickCenter: (lat: number, lng: number) => void;
}

/** Mientras se elige el centro: cursor en cruz y el próximo clic fija el punto. */
function CenterPicker({ active, onPick }: { active: boolean; onPick: (lat: number, lng: number) => void }) {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    container.style.cursor = active ? 'crosshair' : '';
    return () => {
      container.style.cursor = '';
    };
  }, [map, active]);

  useMapEvents({
    click(event) {
      if (active) onPick(event.latlng.lat, event.latlng.lng);
    },
  });

  return null;
}

export default function MapView({
  potholes,
  selectedId,
  onSelectPothole,
  searchArea,
  isPickingCenter,
  onPickCenter,
}: MapViewProps) {
  return (
    <MapContainer center={ENCARNACION_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <LocateControl />
      <CenterPicker active={isPickingCenter} onPick={onPickCenter} />

      {searchArea && (
        <>
          <Circle
            center={[searchArea.lat, searchArea.lng]}
            radius={searchArea.radiusMeters}
            interactive={false}
            pathOptions={{ color: '#0284c7', weight: 2, fillColor: '#0ea5e9', fillOpacity: 0.08, dashArray: '6 6' }}
          />
          <CircleMarker
            center={[searchArea.lat, searchArea.lng]}
            radius={5}
            interactive={false}
            pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#0284c7', fillOpacity: 1 }}
          />
        </>
      )}

      {potholes.map((pothole) => {
        const meta = SEVERITY_META[pothole.severity];
        const isSelected = pothole.id === selectedId;

        return (
          <CircleMarker
            key={pothole.id}
            center={[pothole.lat, pothole.lng]}
            radius={isSelected ? meta.radius + 3 : meta.radius}
            // Sin propagar al mapa: el clic en un bache no debe fijar el centro dos veces.
            bubblingMouseEvents={false}
            pathOptions={{
              color: isSelected ? '#0f172a' : meta.color,
              weight: isSelected ? 3 : 1.5,
              fillColor: meta.color,
              fillOpacity: 0.85,
            }}
            eventHandlers={{
              click: (event) => {
                // Eligiendo el centro, un clic sobre un bache usa ese punto como centro.
                if (isPickingCenter) onPickCenter(event.latlng.lat, event.latlng.lng);
                else onSelectPothole(pothole);
              },
            }}
          >
            <Tooltip direction="top" offset={[0, -meta.radius]}>
              {meta.label}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
