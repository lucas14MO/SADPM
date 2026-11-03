# SAD Pothole Map (SPM) - Documentación de la API REST Backend (FASE 7)

Esta documentación describe la API REST desarrollada en **Django + Django REST Framework** para el mapa interactivo de baches de Encarnación.

La base de desarrollo es PostgreSQL + PostGIS ejecutado mediante Docker Compose.
Consulta [README.md](README.md) para crear el contenedor, configurar Django,
aplicar migraciones e importar sesiones procesadas.

---

## URL Base

- **Servidor de Desarrollo**: `http://127.0.0.1:8000/api/`
- **Ruta principal de baches**: `http://127.0.0.1:8000/api/baches/` (alias: `/api/potholes/`)

---

## Modelo de Datos (`Bache`)

El JSON público de `Bache` conserva latitud y longitud como campos numéricos. En
PostGIS, cada bache también tiene un punto `geography(Point, 4326)` indexado para
consultas en metros. Las tablas internas `CaptureSession` y
`PotholeObservation` conservan la procedencia por recorrido y las detecciones
originales; los baches consolidados se recalculan con DBSCAN espacial al importar
una sesión (`eps` inicial de 2.5 m). Las detecciones sin GPS no se incluyen en el
clustering.

Cada objeto bache retornado o enviado posee la siguiente estructura JSON:

```json
{
  "id": 1,
  "gravedad": "critico",
  "radio_estimado": 1.2,
  "latitud": -27.33056,
  "longitud": -55.86667,
  "coordenadas": {
    "lat": -27.33056,
    "lng": -55.86667
  },
  "confianza": 0.94,
  "timestamp_deteccion": "2026-09-01T14:30:00Z",
  "imagen": null,
  "url_imagen_externa": "https://images.unsplash.com/...",
  "url_imagen": "https://images.unsplash.com/...",
  "created_at": "2026-09-06T16:00:00Z",
  "updated_at": "2026-09-06T16:00:00Z"
}
```

### Descripción de Campos

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | Integer | Identificador único del bache (Solo lectura). |
| `gravedad` | String | Severidad del bache. Valores: `"leve"`, `"moderado"`, `"critico"`. |
| `radio_estimado` | Float | Radio aproximado del bache en metros (ej. `0.5`). |
| `latitud` | Float | Coordenada geográfica de latitud. |
| `longitud` | Float | Coordenada geográfica de longitud. |
| `coordenadas` | Object | Objeto derivado `{ "lat": Float, "lng": Float }` optimizado para Leaflet.js. |
| `confianza` | Float | Confianza del modelo de detección IA entre `0.0` y `1.0`. |
| `timestamp_deteccion` | ISO Datetime | Fecha y hora en que se registró el bache. |
| `imagen` | File / URL | Archivo de imagen subido al servidor Django. |
| `url_imagen_externa` | String (URL) | URL remota opcional de la imagen. |
| `url_imagen` | String (URL) | URL absoluta pública resolver para la visualización en el mapa/modal. |

---

## Endpoints de la API

### 1. Listar y Filtrar Baches

- **Método**: `GET`
- **Endpoint**: `/api/baches/`
- **Descripción**: Obtiene la lista de baches registrados. Soporta filtros opcionales de búsqueda espacial por radio y por severidad.

#### Parámetros Query (Query Params)

| Parámetro | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| `lat` | Float | No | Latitud del centro de búsqueda. | `-27.33056` |
| `lng` | Float | No | Longitud del centro de búsqueda. | `-55.86667` |
| `radio` | Float | No | Radio de búsqueda en metros. Default: `1000`. | `500` |
| `gravedad` | String | No | Filtrar por nivel: `leve`, `moderado`, `critico`. | `critico` |

#### Ejemplos de Peticiones

**Consulta por radio espacial (T03AM)**:
```http
GET /api/baches/?lat=-27.33056&lng=-55.86667&radio=500 HTTP/1.1
Host: 127.0.0.1:8000
```

**Ejemplo en JavaScript (`fetch`)**:
```javascript
const lat = -27.33056;
const lng = -55.86667;
const radio = 500; // metros

fetch(`http://127.0.0.1:8000/api/baches/?lat=${lat}&lng=${lng}&radio=${radio}`)
  .then(res => res.json())
  .then(data => console.log("Baches en radio:", data));
```

#### Respuesta Ejemplo (`200 OK`)
```json
[
  {
    "id": 1,
    "gravedad": "critico",
    "radio_estimado": 1.2,
    "latitud": -27.33056,
    "longitud": -55.86667,
    "coordenadas": {
      "lat": -27.33056,
      "lng": -55.86667
    },
    "confianza": 0.94,
    "timestamp_deteccion": "2026-09-01T14:30:00Z",
    "url_imagen": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7"
  }
]
```

---

### 2. Registrar un Nuevo Bache

- **Método**: `POST`
- **Endpoint**: `/api/baches/`
- **Header**: `Content-Type: application/json` (o `multipart/form-data` si envía imagen)

#### Ejemplo Body JSON:
```json
{
  "gravedad": "critico",
  "radio_estimado": 1.1,
  "latitud": -27.33120,
  "longitud": -55.86540,
  "confianza": 0.92,
  "timestamp_deteccion": "2026-09-06T15:00:00Z",
  "url_imagen_externa": "https://ejemplo.com/fotos/bache_101.jpg"
}
```

#### Respuesta Ejemplo (`201 Created`)
Retorna el objeto bache creado con su `id` asignado.

---

### 3. Obtener Detalle de un Bache

- **Método**: `GET`
- **Endpoint**: `/api/baches/{id}/`
- **Respuesta Ejemplo (`200 OK`)**: Retorna el objeto `Bache` individual.

---

### 4. Actualizar un Bache

- **Método**: `PUT` / `PATCH`
- **Endpoint**: `/api/baches/{id}/`

---

### 5. Eliminar un Bache

- **Método**: `DELETE`
- **Endpoint**: `/api/baches/{id}/`
- **Respuesta**: `24 No Content`

---

## Configuración CORS

El servidor tiene habilitado **CORS** para cualquier origen en desarrollo (`CORS_ALLOW_ALL_ORIGINS = True`), permitiendo peticiones desde aplicaciones Frontend React alojadas en `http://localhost:3000`, `http://localhost:5173`, u otros puertos.
