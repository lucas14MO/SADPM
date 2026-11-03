# Backend y base espacial SPM

El backend usa Django y PostgreSQL/PostGIS en contenedores Compose. Ambos servicios
se comunican por una red Docker privada; solo la API se publica en loopback.

## Iniciar API y PostGIS

```bash
cd backend
cp .env.example .env
# Cambia POSTGRES_PASSWORD en .env para tu entorno local.
```

PostGIS no publica un puerto en el host: solo Django puede acceder a
`postgis:5432` por la red interna. La API queda disponible en
`http://127.0.0.1:8000`. Los datos de PostgreSQL y archivos media persisten en
volúmenes Docker. La imagen Django instala GEOS, GDAL y PROJ para GeoDjango.

El flujo recomendado de primera instalación es:

```bash
sudo docker compose build django
sudo docker compose up -d postgis
sudo docker compose run --rm django python manage.py migrate --noinput
sudo docker compose up -d
sudo docker compose ps
sudo docker compose run --rm --no-deps django python manage.py check
sudo docker compose run --rm --no-deps django python manage.py test potholes
```

Al pasar de la configuración anterior, Compose puede recrear el contenedor
PostGIS para quitar la publicación del puerto. El volumen `postgis_data` no se
borra y conserva la base; no ejecutes `docker compose down -v`.

Verifica la API en `http://127.0.0.1:8000/api/baches/`.

Las migraciones habilitan PostGIS, crean las tablas de sesiones/observaciones,
conservan las coordenadas del modelo existente y agregan índices espaciales.
Los baches creados antes de esta migración conservan su PK y no se convierten en
observaciones ni se incluyen automáticamente en deduplicación; siguen siendo
registros manuales/no gestionados.

## Importar una sesión y consolidar baches

El procesador offline de `capture/` produce `processed_potholes.json` y recortes.
Importa una carpeta de sesión así:

```bash
sudo docker compose run --rm \
  -v "$(realpath ../capture/recordings/sesion_AAAAMMDD_HHMMSS):/data/session:ro" \
  django python manage.py import_processed_potholes /data/session
sudo docker compose run --rm \
  -v "$(realpath ../capture/recordings/sesion_AAAAMMDD_HHMMSS):/data/session:ro" \
  django python manage.py import_processed_potholes /data/session \
  --eps-meters 2.5
```

Sustituye `sesion_AAAAMMDD_HHMMSS` por el directorio real de la sesión.

La importación es idempotente por nombre/inicio de sesión y `track_id`. Conserva
observaciones originales, actualiza esa sesión y recalcula los baches consolidados
entre recorridos mediante `ST_ClusterDBSCAN`. Las distancias se calculan en UTM
21S (EPSG:32721), adecuado a la zona de Encarnación. El radio inicial de
agrupación es 2.5 m y cada observación georreferenciada crea un grupo aunque esté
aislada. Las observaciones con coordenadas nulas se guardan, pero no se agrupan.
Cada observación conserva clase, confianza promedio/máxima, cantidad de frames,
timestamp, keyframe y ruta local de evidencia.
Para identificar la sesión usa `session.json.start_utc` o el primer timestamp de
`frames.csv`; así la clave no depende de la ruta absoluta de la carpeta. Si se
mueve una sesión, conserva su nombre y sus timestamps para que se reconozca como
la misma importación.
La identidad de cada consolidado se deriva del conjunto de IDs de observación;
si una recomputación deja iguales sus miembros, conserva la PK del bache. Cuando
los miembros cambian, se actualizan las agrupaciones afectadas y se retiran solo
los consolidados que ya no representan ningún grupo.

La API conserva el contrato de baches existente. Las consultas de radio utilizan
`ST_DWithin` sobre geography y reciben el radio en metros. Las observaciones y
consolidados se administran por Django; no se añade un endpoint de ingesta en
esta fase.

## Respaldo

Crear un respaldo SQL comprimido:

```bash
sudo docker compose exec -T postgis sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

Restaurarlo en una base ya creada:

```bash
gzip -dc backup.sql.gz | sudo docker compose exec -T postgis sh -c \
  'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

No uses `docker compose down -v` salvo que quieras eliminar deliberadamente el
volumen y todos los datos persistidos.