import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet';
import LocateControl from './LocateControl';
import { SEVERITY_META } from '../../utils/severity';
import type { Pothole } from '../../types/pothole';

const ENCARNACION_CENTER: [number, number] = [-27.3306, -55.8657];
const DEFAULT_ZOOM = 14;

interface MapViewProps {
  potholes: Pothole[];
  selectedId: string | null;
  searchCenter: [number, number];
  radiusMeters: number;
  onSelectPothole: (pothole: Pothole) => void;
  onSelectCenter: (center: [number, number]) => void;
}

function CenterPicker({ onSelectCenter }: Pick<MapViewProps, 'onSelectCenter'>) {
  useMapEvents({
    click: ({ latlng }) => onSelectCenter([latlng.lat, latlng.lng]),
  });
  return null;
}

export default function MapView({
  potholes,
  selectedId,
  searchCenter,
  radiusMeters,
  onSelectPothole,
  onSelectCenter,
}: MapViewProps) {
  return (
    <MapContainer center={ENCARNACION_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <LocateControl />
      <CenterPicker onSelectCenter={onSelectCenter} />

      <Circle
        center={searchCenter}
        radius={radiusMeters}
        pathOptions={{ color: '#0f766e', weight: 1.5, fillColor: '#14b8a6', fillOpacity: 0.08 }}
      />
      <CircleMarker
        center={searchCenter}
        radius={6}
        pathOptions={{ color: '#ffffff', weight: 2, fillColor: '#0f766e', fillOpacity: 1 }}
      >
        <Tooltip direction="top">Centro de búsqueda</Tooltip>
      </CircleMarker>

      {potholes.map((pothole) => {
        const meta = SEVERITY_META[pothole.severity];
        const isSelected = pothole.id === selectedId;

        return (
          <CircleMarker
            key={pothole.id}
            center={[pothole.lat, pothole.lng]}
            bubblingMouseEvents={false}
            radius={isSelected ? meta.radius + 3 : meta.radius}
            pathOptions={{
              color: isSelected ? '#0f172a' : meta.color,
              weight: isSelected ? 3 : 1.5,
              fillColor: meta.color,
              fillOpacity: 0.85,
            }}
            eventHandlers={{ click: () => onSelectPothole(pothole) }}
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
