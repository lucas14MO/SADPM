import { useEffect } from 'react';
import { Circle, CircleMarker, MapContainer, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import LocateControl from './LocateControl';
import { SEVERITY_META } from '../../utils/severity';
import type { Pothole } from '../../types/pothole';

const ENCARNACION_CENTER: [number, number] = [-27.3306, -55.8657];
const DEFAULT_ZOOM = 14;
const DEFAULT_MARKER_OPACITY = 0.85;
const MIN_MARKER_OPACITY = 0.25;
const OPACITY_DROP_PER_REPORT = 0.2;

function markerOpacity(voteCount: number): number {
  return Math.max(
    MIN_MARKER_OPACITY,
    DEFAULT_MARKER_OPACITY - Math.max(0, voteCount) * OPACITY_DROP_PER_REPORT,
  );
}

interface MapViewProps {
  potholes: Pothole[];
  selectedId: string | null;
  searchCenter: [number, number];
  radiusMeters: number;
  onSelectPothole: (pothole: Pothole) => void;
  onSelectCenter: (center: [number, number]) => void;
  focusedPothole: Pothole | null;
}

function CenterPicker({ onSelectCenter }: Pick<MapViewProps, 'onSelectCenter'>) {
  useMapEvents({
    click: ({ latlng }) => onSelectCenter([latlng.lat, latlng.lng]),
  });
  return null;
}

function FocusPothole({ pothole }: Pick<MapViewProps, 'focusedPothole'>) {
  const map = useMap();
  useEffect(() => {
    if (pothole) map.setView([pothole.lat, pothole.lng], Math.max(map.getZoom(), 16), { animate: true });
  }, [map, pothole?.id, pothole?.lat, pothole?.lng]);
  return null;
}

export default function MapView({
  potholes,
  selectedId,
  searchCenter,
  radiusMeters,
  onSelectPothole,
  onSelectCenter,
  focusedPothole,
}: MapViewProps) {
  return (
    <MapContainer center={ENCARNACION_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <LocateControl />
      <CenterPicker onSelectCenter={onSelectCenter} />
      <FocusPothole pothole={focusedPothole} />

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
              fillOpacity: markerOpacity(
                (pothole.falsePositiveReports ?? 0) + (pothole.repairedReports ?? 0),
              ),
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
