# Modelos de detección de baches

## V4 monoclass (modelo objetivo del procesamiento offline)

El artefacto `weights/weights_v4_monoclass.pt` fue reportado como entrenado
con YOLO26 Small y una única clase de detección, `pothole`. La composición del
dataset informada para esta versión es:

| Campo | Valor reportado |
| --- | --- |
| Arquitectura/tamaño | YOLO26 Small |
| Clases | 1: `pothole` |
| Imágenes | 386 |
| Imágenes propias | 143 |
| Imágenes seleccionadas del dataset público | 243 |
| Split train/valid/test | No informado |
| Métricas de evaluación | No informadas |
| Licencia del checkpoint/dataset | No verificada |

Estos datos describen el entrenamiento comunicado para V4; no sustituyen el
reporte reproducible ni verifican por sí mismos los metadatos internos del
checkpoint, la procedencia exacta de las 243 imágenes públicas o los derechos
de uso. V4 se usa como detector monoclass en el procesamiento offline; la
severidad se calcula después por ROI y área relativa, no la predice YOLO.

## V3 multiclase (histórico / compatibilidad)

El archivo `weights/weights.pt` (5,2 MB; presente localmente el 7/11/2026) es el
checkpoint multiclase anterior, conservado para reproducibilidad y compatibilidad
con sesiones ya procesadas.
Los datos de Roboflow proporcionados para V3 son:

| Campo | Valor |
| --- | --- |
| Model URL / identificador | `lucas-benitez/pothole-vhmow-bygvr-4-yolo26n-t1` |
| Tipo | YOLO26 Object Detection (Nano) |
| Versión del dataset | 2026-10-26 2:46 PM |
| Actualizado en Roboflow | 26/10/2026, 3:06 PM |
| Licencia | AGPL-3.0 |
| Latencia (Cloud API) | 7,3 ms |
| URL de checkpoint | No indicada (`-`) |

El sufijo `-4` del identificador de Roboflow señala la cuarta iteración de
entrenamiento del proyecto: la tercera se descartó. **V3** es el nombre de la
versión del modelo en este repositorio/proyecto, y corresponde a esa cuarta
iteración; no significa que sea la tercera iteración de Roboflow.

Las notas del proyecto describen un dataset comunitario público purgado
manualmente (~700 imágenes revisadas; 338 seleccionadas, más aumentos), con
división 70/20/10 y etiquetas propias de tres niveles de severidad. El origen
documentado es, por tanto, un entrenamiento del proyecto sobre datos públicos,
no un peso público original. La URL/model card identifica el modelo de
Roboflow, pero no se ha indicado un enlace de descarga del checkpoint ni se ha
verificado que sus bytes coincidan con `weights/weights.pt`. La licencia
reportada para el modelo es AGPL-3.0; confirmar si cubre también el dataset y
los pesos antes de redistribuirlos.

## Versiones y resultados registrados

Las métricas siguientes se transcriben de las notas existentes; no se dispone
en el repositorio de los informes de evaluación, predicciones ni etiquetas de
test para reproducirlas. No se deben presentar como evaluación independiente.

| Modelo | Dataset / configuración | mAP@50 | mAP@50-95 | Precisión | Recall | F1 | Matriz de confusión |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V2 (10/10/2026) | No documentado; una clase | 82,7% | No registrado | 86,4% | 75,5% | 80,6% | No registrada |
| V3 (Roboflow, 26/10/2026; iteración 4) | Dataset versión 2026-10-26 2:46 PM; 338 imágenes seleccionadas + aumentos; 70/20/10; 3 clases | 39,2% | 16,9% | 63,1% | 46,2% | 52,6% | [Matriz etiquetada](Source/matris_confusion_labeled.svg) |
| V4 monoclass | YOLO26 Small; 386 imágenes reportadas (143 propias + 243 públicas seleccionadas); split/métricas pendientes | — | — | — | — | — | — |

La matriz de confusión V3 está disponible como imagen original en
[`Source/matris_confusion.png`](Source/matris_confusion.png) y con leyendas
añadidas en [`Source/matris_confusion_labeled.svg`](Source/matris_confusion_labeled.svg).
Según la convención indicada para esa imagen, las filas son Ground Truth y las
columnas son Prediction. Valores leídos de la matriz original:

| Ground Truth \\ Prediction | `pothole_critical` | `pothole_light` | `pothole_moderate` | `false_negative` |
| --- | ---: | ---: | ---: | ---: |
| `pothole_critical` | 14 | 1 | 0 | 6 |
| `pothole_light` | 0 | 7 | 0 | 10 |
| `pothole_moderate` | 1 | 1 | 8 | 16 |
| `false_positive` | 0 | 9 | 6 | 0 |

Para V3 también se anotaron Object Loss 0,021, Class Loss 3,0211 y Box Loss
2,0772 (época 258; YOLO26 Nano, según las notas). La latencia de 7,3 ms es de
Roboflow Cloud API y no representa el rendimiento local de `weights.pt`. Las pérdidas no sustituyen
las métricas de evaluación. No está especificado si los valores de precisión,
recall y F1 son globales, por clase o promedio, ni sobre qué split se calcularon.

## Evaluación pendiente para el informe

Completar y guardar el informe/exportación de evaluación sobre el conjunto de
test no usado en entrenamiento ni ajuste. La matriz y mAP@50-95 fueron añadidos
con la información disponible; falta conservar los reportes fuente y aclarar si
precisión, recall y F1 son globales, por clase o promedio, y su umbral de
confianza, versión del dataset y fecha. No inferir valores ausentes de los
registros actuales. Los fotogramas propios, si se etiquetan, deben separarse por
recorrido antes de dividirlos para evitar fotogramas casi idénticos entre train
y test. Roboflow y CVAT son opciones de anotación; el reentrenamiento es trabajo
futuro, no un resultado completado.
