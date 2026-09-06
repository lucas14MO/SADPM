# SAD Pothole Map — Frontend

Interfaz web del mapa de baches de Encarnación (Fase 8 de `fases.md`). Por ahora corre
100% con datos de ejemplo; está armada para conectarse a la API Django/PostGIS (Fase 7)
sin tener que tocar componentes de la UI.

## Stack

React + TypeScript + Vite, Tailwind CSS v4, Leaflet / React-Leaflet.

## Cómo correr

```bash
npm install
npm run dev
```

## Estructura

```
src/
  types/       Tipos de dominio (Pothole, Severity, PotholeQueryParams)
  data/        Datos de ejemplo (mockPotholes.ts)
  services/    Capa de acceso a datos. La UI solo conoce PotholeService (interfaz);
               hoy resuelve a MockPotholeService, mañana a ApiPotholeService.
  hooks/       usePotholes: carga + filtrado, desacoplado del componente que lo usa.
  utils/       Formato de fecha/confianza, colores y tamaños por gravedad, geo (haversine).
  components/
    layout/    Header
    map/       MapView (Leaflet), LocateControl (botón de geolocalización)
    filters/   SeverityFilter (chips leve/moderado/crítico = filtro + leyenda)
    details/   PotholeDetailPanel (panel de info al hacer click en un bache)
    common/    Piezas de UI genéricas (ErrorBanner)
```

## Conectar el backend real

1. Copiar `.env.example` a `.env.local`.
2. Poner `VITE_USE_MOCK_DATA=false` y `VITE_API_BASE_URL` apuntando a la API Django.
3. Listo — `src/services/index.ts` resuelve automáticamente a `ApiPotholeService`
   (`src/services/apiPotholeService.ts`), que ya espera el contrato de
   `/api/baches/?lat=&lng=&radio=&gravedad=` descrito en `fases.md` (Fase 7).

Ningún componente de `components/` ni el hook `usePotholes` necesita cambiar: todos
dependen de la interfaz `PotholeService`, no de su implementación.
