# Parte 1 · Reconocimiento de gestos

Reconocimiento de 6 gestos de mano (`ok`, `paper`, `rock`, `rockandroll`, `scissors`, `thumbsup`) con
MediaPipe (21 puntos por mano) y clasificadores entrenados sobre esos puntos. Se ejecuta en **Windows**
(la webcam no funciona bien dentro de WSL).

| Carpeta | Contenido |
|---|---|
| `kit_grabacion/` | Grabador del dataset que usó cada participante (`record_dataset.py`), con su guía |
| `entrenamiento/` | Pipeline propio: preprocesado, rejilla de experimentos, evaluación y exportación (paquete `hgr` + tests) |
| `demo/` | Notebook local (CNN del enunciado) y demo en tiempo real `demo-gestures-PIDS.py` |
| `datos_generados/` | Los CSV de landmarks extraídos de las 3000 imágenes (las imágenes no se versionan) |
| `modelos/` | Modelos exportados (MLP y CNN) y el `.keras` del notebook |
| `resultados/` | Informe de cada experimento, sus tablas en CSV y la comparativa |

## Resultados (evaluando con una persona no vista, LOPO)

| Modelo | Accuracy LOPO | Con la mano contraria |
|---|---|---|
| CNN de la presentación, sin normalizar | 90,9 % | 91,3 % |
| CNN, normalización muñeca + escala + rotación | 95,8 % | 96,0 % |
| **MLP, normalización completa + aumentación con volteo** | **96,5 %** | 96,6 % |

Dataset: 5 participantes, 100 imágenes por gesto y persona (3000 en total), 97,7 % con mano detectada.

## Reproducir

El dataset de imágenes y las tomas originales no están en el repositorio (solo los CSV de landmarks).
Con las imágenes disponibles, desde `entrenamiento/`:

```bash
python preprocesar.py          # extrae landmarks y comprueba la calidad
python entrenar_todo.py        # plan completo (unos 50 min en una RTX 5070)
```

La demo necesita además `hand_landmarker.task` de MediaPipe (7,5 MB), que se descarga de Google.

La conexión con las partes 2 y 3 está en [`../integracion/`](../integracion/).
