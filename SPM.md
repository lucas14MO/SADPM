# Sistema de Deteccion y Mapeo Automatico de Baches (SAD Pothole Map - optativo)

## Contexto Local
El estado de la capa asfaltica de Encarnacion es un gran problema prioritario de insfraestructura y seguridad vial.

## Objetivo
Clasificar y geolocalizar daños(baches, fisura severas) en la calzada procesando viedo grabado desde una camara montada en un vehiculo.

## Desafio Tecnico
Deteccion de objetos en video en tiempo real. Extraer los fotogramas clave, asociados a las coordenadas GPS de la grabacion y evitar duplicados de un mismo bache.

## Entregable
Mapa interactivo de la ciudad donde se señalan los baches detectados clasificados por gravedad (leve, moderado, critico).

# Tareas e Investigacion

## App de mapa interactivo (React + Leaflet.js / Django + PostgreSQL)

### T01AM - Frontend
Crear una app frontend en React para mostrar un mapa interactivo de Encarnación utilizando Leaflet.js. 
- El mapa debe permitir la navegación interactiva (zoom, pan, centrado).
- Debe mostrar las rutas, calles y capas de mapas (OpenStreetMap / CartoDB).
- La app debe acceder a la ubicación del usuario y marcarla en el mapa.

### T02AM - Frontend
Implementar el marcado y visualización de puntos que representen baches.
- El usuario debe poder seleccionar un punto en el mapa para mostrar los baches en un radio configurable alrededor del mismo.
- Los puntos deben pintarse con colores y tamaños representativos del nivel de gravedad del bache (verde: leve, amarillo: moderado, rojo: crítico).
- La posición de cada punto debe correlacionarse exactamente con coordenadas geográficas (latitud, longitud).
- Mostrar popup/modal con el recorte del keyframe y la caja dibujada, fecha, confianza y severidad calculada.
- Permitir reportar un falso positivo o indicar que el bache fue reparado/desactualizado; ocultar en el mapa los baches invalidados por el backend.

### T03AM - Backend
Crear una API REST en Django + PostgreSQL (PostGIS) para almacenar y consultar los datos de los baches.
- La app frontend debe poder consumir la API para consultar baches por radio espacial (`/api/baches/?lat=...&lng=...&radio=...`).
- Los baches deben almacenar: `id`, severidad determinista (leve/moderado/crítico), `radio_estimado`, coordenadas, confianza YOLO, `timestamp_deteccion`, URL/archivo de evidencia, contadores de reportes y estado de validez/visibilidad.
- Incorporar endpoint de feedback y purga lógica/ocultamiento: invalidar con al menos 3 reportes de falso positivo o al marcarse como reparado/desactualizado; definir una política para evitar votos duplicados.

## IA y Entrenamiento

### T01IE - Recolección y Preparación del Dataset
- Recolectar datos en campo grabando recorridos por calles de Encarnación de día y con buena iluminación.
- Seleccionar e integrar datasets públicos de baches (Roboflow Universe, Kaggle) para ampliar la diversidad de asfalto y condiciones.
- Limpiar el dataset filtrando imágenes duplicadas, muy borrosas o irrelevantes.

### T02IE - Etiquetado y Augmentation de Datos
- Etiquetar los baches mediante herramientas de anotación (Roboflow / CVAT / LabelImg) en formato YOLO (bounding boxes).
- Definir criterios de etiquetado por clases de gravedad (leve, moderado, crítico) o clase unificada de bache.
- Aplicar Data Augmentation (flip horizontal, variaciones de brillo/contraste, rotación leve, cambios de escala).
- Dividir el conjunto de datos en subconjuntos de Entrenamiento (70%), Validación (20%) y Prueba (10%).

### T03IE - Entrenamiento del Modelo de Detección (YOLO)
- Configurar y entrenar un modelo de arquitectura YOLO (YOLOv8 o YOLOv11 de Ultralytics) usando Python y PyTorch.
- Ajustar hiperparámetros (número de epochs, batch size, learning rate, tamaño de entrada 640x640).
- Monitorear curvas de pérdida (box loss, cls loss, dfl loss) durante el entrenamiento.

### T04IE - Evaluación y Ajuste del Modelo
- Evaluar el modelo entrenado con el conjunto de prueba usando métricas estándar: mAP@50, mAP@50-95, Precision y Recall.
- Generar matriz de confusión para identificar falsos positivos (sombras, manchas de aceite, parches) y falsos negativos.
- Ajustar los umbrales de confianza (confidence threshold) e IoU para optimizar la tasa de detección.

### T05IE - Clasificación de Gravedad del Bache
- Definir e implementar el criterio de clasificación de gravedad:
  - Filtrar detecciones fuera de la ROI del asfalto usando el centroide vertical; como valor inicial, descartar si `Y_center < 0.45 × H`.
  - Calcular `A_norm = A / (W × H) × f(Y_center)` para corregir el área del bounding box por perspectiva.
  - Determinar la severidad del keyframe representativo con umbrales configurables para `leve`, `moderado` y `critico`; calibrar la corrección y los umbrales por montaje.
- Mantener la confianza YOLO separada de la severidad y documentar las limitaciones de estimar tamaño con cámara monocular.

## Procesado de Imagen

### T01PI - Extracción y Selección de Fotogramas (Keyframes)
- Desarrollar script en Python con OpenCV para procesar archivos de video grabados (`.mp4`, `.avi`).
- Implementar extracción de fotogramas a una tasa configurable (ej. 5 a 10 FPS o 1 frame cada N fotogramas) para reducir redundancia computacional.

### T02PI - Preprocesamiento y Control de Calidad
- Aplicar redimensionamiento de imagen a la resolución nativa del modelo (640x640) conservando la proporción de aspecto.
- Normalizar canales de color (RGB) y contraste si fuera necesario.
- Implementar algoritmo de detección de desenfoque (ej. varianza del Laplaciano en OpenCV) para descartar fotogramas movidos por vibración del vehículo.
- Aplicar la ROI del asfalto antes de consolidar detecciones y guardar como evidencia el recorte del keyframe representativo, con su caja visible.

## Grabado y Procesamiento de Video

### T01GP - Captura de Video y Sincronización GPS
- Definir el esquema de montaje de la cámara en la parte frontal/parabrisas del vehículo con ángulo hacia la calzada.
- Grabar el track GPS en paralelo mediante una aplicación de GPS logging en smartphone o módulo GPS dedicado (generando archivo `.gpx` o `.csv` con timestamps en UTC/hora local).
- Implementar protocolo de sincronización de relojes entre la cámara de video y el registrador GPS previo a cada grabación.

### T02GP - Inferencia en Video y Tracking Temporal (ByteTrack / BoT-SORT)
- Ejecutar el pipeline de inferencia offline sobre el video procesando los fotogramas con el modelo YOLO entrenado.
- Integrar algoritmo de seguimiento/tracking de objetos (ByteTrack o BoT-SORT integrado en Ultralytics) para asignar un ID único a cada bache mientras permanece en el campo de visión.
- Garantizar que un mismo bache visible durante 15 o 30 frames continuos sea contado como una sola detección válida en ese paso.

### T03GP - Sincronización Temporal Video ↔ GPS (Georreferenciación)
- Desarrollar script de interpolación de datos GPS basado en el timestamp de cada frame donde se detecta un bache clave.
- Asociar a cada bache su coordenada geográfica calculada (latitud, longitud, altitud aproximada).

### T04GP - Deduplicación Espacial
- Implementar algoritmo de clustering espacial (DBSCAN en Python o PostGIS ST_ClusterDBSCAN en PostgreSQL) sobre las coordenadas de baches detectados.
- Unificar detecciones de un mismo bache registradas en diferentes pasadas o recorridos por la misma calle (radio de agrupación de 2-3 metros).
- Base acordada: PostgreSQL + PostGIS en contenedor Docker Compose; se conservan observaciones por sesión y se recalculan baches consolidados con `eps=2.5 m` configurable.

### T05GP - Carga Masiva y Sincronización con Backend Django
- Importar las sesiones procesadas al backend Django/PostGIS mediante el comando batch vigente, conservando la evidencia y asociando su ruta/URL a cada bache.
- Integrar el registro de feedback ciudadano y la exclusión de baches invalidados/desactualizados de las consultas públicas.