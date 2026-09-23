# SPM — Captura de video (Fase 1)

Herramienta para grabar video desde cualquier cámara conectada al equipo y dejar
los timestamps necesarios para sincronizarlo con el track GPS.

Acepta cualquier dispositivo que el sistema reconozca como cámara (UVC):
webcam integrada, webcam USB, cámara de acción / dashcam en modo webcam,
capturadora HDMI‑USB para cámaras con salida HDMI, o cámaras virtuales (OBS,
DroidCam para usar un smartphone).

## Instalación

```powershell
cd capture
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```powershell
python capture.py --list                 # ver cámaras detectadas (índice + nombre)
python capture.py                        # elegir cámara y abrir vista previa
python capture.py --camera 1             # usar directamente la cámara 1
python capture.py --camera 1 --width 1280 --height 720 --fps 30
python capture.py --camera 1 --record --no-preview       # grabar sin ventana, Ctrl+C para parar
python capture.py --camera 1 --record --duration 600     # grabar 10 min y salir
```

En la vista previa: **R** inicia/detiene la grabación, **Q** o **ESC** sale.
La superposición (hora UTC, fps, REC) solo se muestra en pantalla, no se graba.

Se piden 1920×1080 @ 30 fps en formato MJPG por defecto; si la cámara no lo
soporta, el driver usa el modo más cercano (se informa al iniciar).
`--no-mjpg` desactiva MJPG si alguna cámara da problemas con ese formato.

## Salida

Cada grabación crea `recordings/sesion_AAAAMMDD_HHMMSS/`:

| Archivo | Contenido |
| --- | --- |
| `video.mp4` | Video grabado. |
| `frames.csv` | `frame, t_rel_s, epoch_s, utc` — hora UTC de cada fotograma. |
| `session.json` | Cámara, resolución, fps nominal y real, duración, inicio/fin UTC. |

`frames.csv` es la referencia para la Fase 5: para ubicar un bache detectado en
el fotograma *N*, se busca su hora UTC y se interpola la posición en el `.gpx`.
Se usa esta tabla (y no `N / fps`) porque las cámaras USB no entregan fps
perfectamente constantes.

## Protocolo de sincronización con el GPS

1. Antes de salir, sincronizar la hora de la laptop (Windows: *Configuración →
   Hora e idioma → Sincronizar ahora*). El GPS toma la hora de los satélites.
2. Iniciar el GPS logger (smartphone o módulo) y esperar fix estable.
3. Iniciar la grabación con `capture.py`.
4. Verificación: filmar unos segundos la pantalla del GPS logger mostrando su
   hora; comparar con la hora en `frames.csv` para medir el desfase residual.
   Si es mayor a ~0,5 s, anotarlo para corregirlo en la georreferenciación.
5. Al terminar, detener la grabación y luego el logger. Guardar el `.gpx` /
   `.csv` del GPS dentro de la carpeta de la sesión.

## Problemas comunes

- **No aparece la cámara**: probar otro puerto/cable USB (algunos cables solo
  cargan, sin datos) y verificar que la cámara esté en modo webcam/UVC.
- **"No se pudo abrir la cámara"**: cerrar otras apps que la estén usando
  (Zoom, Teams, navegador, app Cámara de Windows).
- **fps bajos**: poca luz aumenta la exposición y baja los fps; también el
  puerto USB 2.0 limita la resolución sin MJPG.
