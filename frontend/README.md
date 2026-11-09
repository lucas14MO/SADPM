# SAD Pothole Map — Frontend

Interfaz web del mapa de baches de Encarnación y calibración manual de severidad.
El mapa puede usar datos de ejemplo o la API Django/PostGIS; la pantalla de
clasificación requiere el backend real y una cuenta Django con permisos staff.

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
  hooks/       usePotholes: carga espacial + filtrado por gravedad.
  utils/       Formato de fecha/confianza, colores y tamaños por gravedad, geo (haversine).
  components/
    layout/    Header con navegación entre mapa y calibración
    map/       MapView (Leaflet), selección de centro y radio, LocateControl
    filters/   SeverityFilter (chips leve/moderado/crítico = filtro + leyenda)
    details/   Panel de detalle, modal de baches con votos y visor de evidencia
    calibration/ ClassificationPage: etiquetas humanas de recortes y CSV
    common/    Piezas de UI genéricas (ErrorBanner)
```

## Conectar el backend real

1. Copiar `.env.example` a `.env.local`.
2. Poner `VITE_USE_MOCK_DATA=false` y `VITE_API_BASE_URL` apuntando a la API Django.
3. Listo — `src/services/index.ts` resuelve automáticamente a `ApiPotholeService`
   (`src/services/apiPotholeService.ts`), que ya espera el contrato de
   `/api/baches/?lat=&lng=&radio=&gravedad=` descrito en `fases.md` (Fase 7).

En el mapa, un clic fija el centro de consulta y el control numérico modifica el
radio en metros. La vista Calibración consulta
`/api/observaciones/clasificacion/`; inicia sesión con una cuenta staff en
`http://127.0.0.1:8000/admin/` antes de usarla. Aplica en el backend la migración
pendiente antes de habilitar este flujo.
