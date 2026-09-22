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
`C:\Users\Javier\PIDS_HandPose\kit-grabacion\HAR_mediapipe\data`, y el resto del grupo las tiene en la
[copia de seguridad](#copia-de-seguridad-del-dataset). Se indican con `PIDS_DATOS` (o con `--datos`), así que
cada uno puede tenerlas donde quiera.

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

Para que la demo confirme o cancele consultas del chatbot, la plataforma tiene que estar levantada en WSL
con `GESTOS_ACTIVOS=true` y, en esta misma consola de Windows, la clave de captura:

```powershell
$env:PIDS_CLAVE_GESTOS = "<CAPTURA_CLAVE_GESTOS del .env>"
# $env:PIDS_CAPTURA_URL = "http://localhost:8001"   # ya es el valor por defecto
```

Sin esa variable no se envía nada: la demo de la parte 1 funciona igual. Detalle del ciclo en
[`integracion/README.md`](../integracion/README.md).

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

## Copia de seguridad del dataset

El dataset no se puede volver a grabar (cinco personas, una tarde), así que hay una copia comprimida y
verificada fuera del portátil (T01).

| | |
|---|---|
| Fichero | `dataset_gestos_PIDS_2026-09-16.zip`, 598,9 MiB (sin compresión: las JPEG no ganan nada) |
| Dónde | Enlace compartido solo con el grupo: *pendiente, lo añade Javier al subirla* |
| SHA-256 | `886cfa3ed1cf5f055e0550b4b263d8f0ae3c267bfe83f09374db1eb942e31a9b` |
| Contenido | `data/` con las 5 tomas completas (p1 a p5: 600 imágenes y `metadata.json` cada una, 3000 imágenes), `LEEME.txt` y `MANIFIESTO.sha256` con el SHA-256 de cada fichero |
| Fuera de la copia | Cuatro tomas interrumpidas o vacías (0, 6, 0 y 0 imágenes), que tampoco usa el entrenamiento |

Son fotos de las cinco personas del grupo: **no se publica**, ni en este repositorio (que es público) ni con
un enlace abierto a cualquiera.

```powershell
# Comprobar la descarga: tiene que salir el SHA-256 de la tabla
(Get-FileHash dataset_gestos_PIDS_2026-09-16.zip -Algorithm SHA256).Hash

# Descomprimir y usarla como cualquier otra carpeta de datos
Expand-Archive dataset_gestos_PIDS_2026-09-16.zip -DestinationPath C:\PIDS\copia_dataset
$env:PIDS_DATOS = "C:\PIDS\copia_dataset\data"
python parte1_gestos\entrenamiento\preprocesar.py
```

Para comprobar imagen a imagen, dentro de la carpeta descomprimida y desde WSL o Git Bash:
`sha256sum -c MANIFIESTO.sha256`.

Verificada el 21/09/2026: descomprimida en otra carpeta, los 3005 ficheros coinciden con el manifiesto y
`preprocesar.py`, ejecutado desde una copia limpia del repositorio sobre la copia, da lo mismo que sobre el
original: 5 tomas completas, 3000 imágenes y 2931 con mano (97,7 %).

La conexión con las partes 2 y 3 está en [`../integracion/`](../integracion/).
