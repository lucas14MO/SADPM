# Tareas pendientes

> Las pruebas con datos reales quedan pendientes hasta disponer de una sesión
> de video y su GPX. No intentar cerrar la validación end-to-end ni registrar
> métricas de campo sin esos datos.

## 4. Detector determinista por ROI y área relativa — Media

- [x] Aplicar ROI configurable al pipeline offline (`Y_center < 0.45 × H` por defecto) y probar detecciones por encima/en el límite.
- [x] Calcular `A_norm = A / (W × H) × f(Y_center)` con factor de perspectiva y parámetros configurables; defaults documentados.
- [x] Seleccionar por track el keyframe de mayor área dentro de ROI, desempatar por confianza y usarlo para severidad, evidencia, timestamp y geolocalización.
- [x] Asignar severidad canónica con umbrales configurables y cubrir los límites en pruebas sintéticas. Umbrales calibrados por el equipo (`0.001` / `0.008`, 9/11) con la pestaña Calibración y `recalcular_severidad`. **Pendiente:** calibrar el factor de perspectiva `f`.
- [x] Separar confianza YOLO de severidad en `processed_potholes.json`; el importador acepta severidad canónica y conserva compatibilidad con etiquetas V3.

## 5. Evidencia y recortes — Media

- [x] Guardar `crops/bache_NNNN.jpg` del keyframe seleccionado con la caja dibujada.
- [x] Exportar en JSON ruta, severidad, área normalizada y confianza; copiar la evidencia a MEDIA durante importación.
- [x] Alinear recorte, archivo persistente y URL pública del bache consolidado.

## Modelo IA: origen, dataset y métricas — Baja

- [x] Registrar la procedencia reportada de V3, arquitectura, dataset descrito y métricas disponibles en [weights/IA_Models.md](weights/IA_Models.md).
- [x] Registrar URL/identificador, iteración de entrenamiento, versión de dataset, tipo y latencia Cloud API de Roboflow en [IA_Models.md](weights/IA_Models.md).
- [x] Registrar la licencia reportada del modelo (AGPL-3.0).
- [x] Registrar los datos reportados de V4 monoclass (YOLO26 Small; 386 imágenes, 143 propias y 243 públicas seleccionadas) sin inferir métricas o licencia.
- [x] Verificar los checkpoints contra Roboflow (fechas internas coinciden: V3 = iteración 4, V4 = iteración 9) y guardar los SHA-256 en [IA_Models.md](weights/IA_Models.md).
- [X] Confirmar si la licencia AGPL-3.0 cubre también el dataset.
- [x] Añadir el mAP@50-95 (16,9%) y documentar la matriz de confusión con sus etiquetas y conteos en [IA_Models.md](weights/IA_Models.md).
- [x] Registrar métricas de V4: mAP por tamaño (Roboflow), P/R/mAP de validación del checkpoint, pérdidas y latencia local en CPU.
- [x] Matriz de confusión de V4 en test (Roboflow, 37 imágenes): P 76,3 %, R 64,3 %, F1 69,8 % en [IA_Models.md](weights/IA_Models.md).

## 7. Backend: feedback y purga lógica — Media

- [x] Añadir contadores, visibilidad, `area_norm`, evidencia persistente y entidad de feedback con migración `0003`.
- [x] Exponer feedback por tipo/token UUID, idempotente por bache, tipo y cliente.
- [x] Ocultar al alcanzar `3` reportes de falso positivo o el primer reporte de reparación/desactualización.
- [x] Excluir ocultos de consultas públicas y probar endpoint, umbral y conservación/reasignación al reconstruir o dividir clusters en PostgreSQL/PostGIS.
- [x] Aplicar/verificar la migración `0003` en el entorno PostGIS.

## 8. Frontend: revisión y validación ciudadana — Media

- [x] Mostrar en el detalle evidencia, severidad y confianza.
- [x] Añadir acciones de feedback con estados de envío/error y bloqueo repetido en la vista actual; backend aplica idempotencia por UUID.
- [x] Recargar el mapa y cerrar el detalle cuando backend oculta el bache.
- [x] Reducir progresivamente la opacidad del marcador según el total de reportes ciudadanos; los baches reparados/desactualizados se ocultan según la política existente.
- [x] Derivar los contadores de feedback persistido para compartir conteos entre navegadores; refrescar el mapa al recuperar foco y cada 15 segundos.
- [x] Añadir modal de acceso rápido a baches con reportes de falso positivo o reparación, incluidos los ocultos.
- [x] Simular votos creando registros de feedback desde el inline de Django Admin.
- [x] Compilar el frontend (`npm run build` OK).
- [ ] Probar la UI en el navegador con datos reales (marcadores, filtro, foto, feedback).

## 9. Documentación y presentación — Baja

- [x] Corregir estados de deduplicación e importación: DBSCAN espacial está implementado en el backend y `import_processed_potholes` importa sesiones procesadas y reconstruye consolidados.
- [x] Añadir protocolo reproducible de sincronización GPS y guía de montaje/calibración de cámara a [DOCUMENTACION.md](DOCUMENTACION.md). Las medidas reales del montaje y los ajustes del logger deben anotarse en campo; no están en el repositorio.
- [x] **Conectar el mapa a la API real — Media.** En `frontend/.env.local`, configurar `VITE_USE_MOCK_DATA=false` y `VITE_API_BASE_URL` con la URL base del backend (por ejemplo `http://127.0.0.1:8000/api`). Verificar marcadores por color, filtro de severidad, foto con caja y acciones de feedback.
- [ ] **Prueba completa con datos reales — parcial.** Hecha con 403 fotogramas + GPX del 7/11 (89 baches en el mapa); falta un recorrido en video a 30 fps. Ejecutar video → `process_video.py` → importar sesión en PostGIS → comprobar resultados en el mapa. Registrar errores y resultado; dejar los testeos pendientes hasta contar con una sesión procesable.
- [x] Documentar el procedimiento de campo del 7/11/2026 (vehículo con conductor y operador, laptop con `capture.py`, calibración previa sobre el asfalto, GPX exportado desde una aplicación de iOS) en la sección 11 de [DOCUMENTACION.md](DOCUMENTACION.md).
- [ ] Completar la ficha de campo con el nombre y la versión de la aplicación GPS, la frecuencia de registro y el modelo de cámara.
- [ ] Preparar y revisar el manual de uso durante una ejecución completa siguiendo [DOCUMENTACION.md](DOCUMENTACION.md), incluida la importación descrita en `backend/README.md` (validación práctica pendiente de datos reales).
