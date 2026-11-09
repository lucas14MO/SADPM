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
  "area_norm": 0.012,
  "timestamp_deteccion": "2026-09-01T14:30:00Z",
  "imagen": null,
  "url_imagen_externa": "https://images.unsplash.com/...",
  "url_imagen": "https://images.unsplash.com/...",
  "false_positive_reports": 0,
  "repaired_reports": 0,
  "is_visible": true,
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
| `area_norm` | Float / null | Área normalizada usada por el clasificador determinista de severidad. |
| `timestamp_deteccion` | ISO Datetime | Fecha y hora en que se registró el bache. |
| `imagen` | File / URL | Archivo de imagen subido al servidor Django. |
| `url_imagen_externa` | String (URL) | URL remota opcional de la imagen. |
| `url_imagen` | String (URL) | URL absoluta pública resolver para la visualización en el mapa/modal. |
| `false_positive_reports` | Integer | Reportes ciudadanos de falso positivo. |
| `repaired_reports` | Integer | Reportes de reparación/desactualización. |
| `is_visible` | Boolean | Si el bache sigue visible en consultas públicas. |

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

### 6. Enviar feedback ciudadano

- **Método**: `POST`
- **Endpoint**: `/api/baches/{id}/feedback/`
- **Autenticación**: no requiere cuenta; recibe un UUID estable generado por el
  navegador para limitar reportes repetidos ordinarios (no es control antifraude).

```json
{
  "feedback_type": "false_positive",
  "client_token": "4c0992b7-3eed-40ae-ae9a-566ef0373ad0"
}
```

`feedback_type` acepta `false_positive` o `repaired`. La combinación de bache,
tipo y token es idempotente. Al llegar a 3 reportes distintos de falso positivo
o al primer reporte de reparación, `is_visible` pasa a `false` y el bache deja de
aparecer en la lista pública. La respuesta incluye `created`, ambos contadores y
`is_visible`.

Los reportes pertenecen al bache consolidado. Al reconstruir clusters espaciales,
se reasocian al nuevo grupo con mayor solapamiento de observaciones; en caso de
división se asignan a un único grupo para evitar duplicar votos.

### 7. Clasificar observaciones para calibración

Requiere una sesión Django autenticada y un usuario con `is_staff=True`. Inicia
sesión en `/admin/` y conserva las cookies de sesión y CSRF al llamar a la API.

**Listar muestras**

- **Método**: `GET`
- **Endpoint**: `/api/observaciones/clasificacion/`
- **Respuesta**: observaciones con recorte y `area_norm`, con las muestras sin
  etiqueta humana al principio.

Cada elemento incluye `id`, `session_key`, `track_id`, `severity` calculada,
`human_severity`, `area_norm`, confianza, cantidad de frames, timestamp,
`evidence_image`, usuario clasificador y fecha de clasificación.

**Guardar etiqueta humana**

- **Método**: `PATCH`
- **Endpoint**: `/api/observaciones/clasificacion/{id}/`
- **Header**: `X-CSRFToken` obtenido de la cookie `csrftoken`.

```json
{
  "human_severity": "moderado"
}
```

`human_severity` acepta `leve`, `moderado` o `critico`. Esta etiqueta no cambia
`severity`; la pantalla permite exportar a CSV el ID de observación, sesión,
track, `area_norm` y clase humana.

### 8. Recalcular severidad

El comando `python manage.py recalcular_severidad --light-threshold 0.001
--critical-threshold 0.005 --dry-run` muestra cuántas observaciones existentes
se actualizarían. Al quitar `--dry-run`, actualiza las severidades desde
`area_norm` y reconstruye los consolidados, sin volver a procesar videos. Las
observaciones con área nula y los baches manuales quedan fuera.

---

## Configuración CORS

El servidor tiene habilitado **CORS** para cualquier origen en desarrollo
(`CORS_ALLOW_ALL_ORIGINS = True`) y credenciales para la sesión interna. Los
orígenes frontend confiables para CSRF se configuran en
`DJANGO_CSRF_TRUSTED_ORIGINS` (default: puertos `5173` y `5174` en `localhost` y
`127.0.0.1`). En producción restringe CORS y configura únicamente los orígenes
reales.
