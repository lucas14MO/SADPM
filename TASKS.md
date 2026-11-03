#### Fase 6: Deduplicación Espacial (DBSCAN) [⏳ Pendiente]

Actualmente, el script `process_video.py` exporta los baches únicos *por sesión* en `processed_potholes.json`, pero no resuelve qué pasa si el vehículo pasa dos veces por la misma calle en sesiones diferentes.

* **Implementar clustering geográfico:** Desarrollar un script (o un proceso en el backend) que lea las coordenadas (`latitude`, `longitude`) de las detecciones, preferiblemente usando `PostGIS ST_ClusterDBSCAN` o `scikit-learn DBSCAN`.
* **Definir umbral de proximidad:** Establecer un radio (ej. 2 a 3 metros) para considerar que múltiples detecciones corresponden al mismo bache físico.
* **Lógica de consolidación:** Cuando se agrupen baches duplicados, programar la lógica para conservar el registro con la mayor confianza (`confidence_max`) o la imagen (`evidence_image`) más clara, descartando los demás.



#### Fase 9: Integración End-to-End (Ingesta al Backend) [⏳ Pendiente]

El backend de Django ya está desarrollado (`backend/`), pero falta el puente automatizado entre los resultados de la Fase 5 y la API.

* **Desarrollar script de ingesta (Data Loader):** Crear un script (ej. `upload_to_api.py`) que lea el archivo `processed_potholes.json` generado en la Fase 5.


* **Mapeo de datos para la API:**
* Traducir la clase `severity` de YOLO (`pothole_light`, `pothole_moderate`, `pothole_critical`) a las opciones esperadas por Django (`leve`, `moderado`, `critico`).


* Mapear `utc` del `mejor_frame` al campo `timestamp_deteccion`.


* Mapear `confianza_max` a `confianza`.


* Asegurar que las imágenes de evidencia (`crops/bache_NNNN.jpg`) se carguen correctamente al *endpoint* mediante solicitudes `multipart/form-data`.




* **Manejo de excepciones GPS:** Programar la lógica para ignorar o manejar de forma especial los baches que quedaron fuera de la cobertura del `.gpx` y tienen `latitude`/`longitude` nulas (`null`).



#### Refinamiento Geométrico y Documentación (Opcional pero Recomendado)

* **Compensación de posición (Offset de cámara):** Dado que la coordenada GPS registrada corresponde a la posición del teléfono/antena y el bache detectado está metros adelante en el campo de visión de la cámara, podrías investigar cómo proyectar un desplazamiento (*offset*) en la dirección de la marcha basándote en la velocidad y el *heading* del track GPS.


* **Documentación de hardware:** Documentar el protocolo exacto de montaje de la cámara en el vehículo y la configuración del GPS Logger utilizado en campo para asegurar repetibilidad.