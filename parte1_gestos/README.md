# Parte 1 · Reconocimiento de gestos

Reconocimiento de 6 gestos de mano (`ok`, `paper`, `rock`, `rockandroll`, `scissors`, `thumbsup`) con
MediaPipe (21 puntos por mano) y clasificadores entrenados sobre esos puntos. **Esta parte se ejecuta en
Windows**, porque la webcam no funciona bien dentro de WSL (las partes 2 y 3 sí van en WSL).

| Carpeta | Contenido |
|---|---|
| `kit_grabacion/` | Grabador del dataset que usó cada participante (`record_dataset.py`), con su guía |
| `entrenamiento/` | Pipeline propio: preprocesado, rejilla de experimentos, evaluación y exportación (paquete `hgr` + tests) |
| `demo/` | Demo en tiempo real `demo-gestures-PIDS.py` y el notebook local (CNN del enunciado) |
| `datos_generados/` | CSV de landmarks extraídos de las 3000 imágenes (las imágenes no se versionan) |
| `modelos/` | Modelos exportados (MLP y CNN) y el `.keras` del notebook |
| `resultados/` | Informe de cada experimento, sus tablas en CSV y la comparativa |

## Resultados (evaluando con una persona no vista, LOPO)

| Modelo | Accuracy LOPO | Con la mano contraria |
|---|---|---|
| CNN de la presentación, sin normalizar | 90,9 % | 91,3 % |
| CNN, normalización muñeca + escala + rotación | 95,8 % | 96,0 % |
| **MLP, normalización completa + aumentación con volteo** | **96,5 %** | 96,6 % |

Dataset: 5 participantes, 100 imágenes por gesto y persona (3000 en total), 97,7 % con mano detectada.

## Cómo ejecutarlo desde el repositorio (Windows)

Las 3000 imágenes y las tomas originales **no están en el repositorio**: siguen en
`C:\Users\Javier\PIDS_HandPose\kit-grabacion\HAR_mediapipe\data`. Se indican con `PIDS_DATOS` (o con
`--datos`), así que cada uno puede tenerlas donde quiera.

```powershell
# 1. Modelo de MediaPipe (7,8 MB, no se versiona)
C:\Users\Javier\PIDS_HandPose\.venv\Scripts\python.exe parte1_gestos\descargar_modelos.py

# 2. Dónde están las imágenes (varias carpetas separadas por ;)
$env:PIDS_DATOS = "C:\Users\Javier\PIDS_HandPose\kit-grabacion\HAR_mediapipe\data"

# 3. Extraer landmarks y comprobar la calidad de las tomas
C:\Users\Javier\PIDS_HandPose\.venv\Scripts\python.exe parte1_gestos\entrenamiento\preprocesar.py

# 4. Entrenar (rejilla reducida; entrenar_todo.py hace el plan completo, ~50 min en una RTX 5070)
C:\Users\Javier\PIDS_HandPose\.venv\Scripts\python.exe parte1_gestos\entrenamiento\entrenar.py --rapido --nombre prueba

# 5. Demo en tiempo real (abre la webcam; q para salir)
C:\Users\Javier\PIDS_HandPose\.venv\Scripts\python.exe parte1_gestos\demo\src\demo-gestures-PIDS.py
```

El entorno de Python (`.venv` con MediaPipe 0.10.35, Keras 3 sobre PyTorch y CUDA) es el que ya está
creado en `C:\Users\Javier\PIDS_HandPose`. Sus dependencias exactas están en
`entrenamiento/requirements.txt`, por si hay que rehacerlo en otro equipo.

Para probar la demo sin cámara, sobre fotos ya grabadas:

```powershell
C:\Users\Javier\PIDS_HandPose\.venv\Scripts\python.exe parte1_gestos\demo\src\demo-gestures-PIDS.py --imagenes <carpeta con subcarpetas por gesto> --sin-ventana
```

Comprobado el 17/09/2026 desde una copia limpia del repositorio: preprocesado de las 5 tomas (2931
imágenes con mano), entrenamiento rápido (CNN 95,7 % en LOPO) y demo sobre las imágenes de test
(95,2 % de aciertos).

La conexión con las partes 2 y 3 está en [`../integracion/`](../integracion/).
