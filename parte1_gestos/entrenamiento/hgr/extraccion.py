"""JPG -> landmarks de MediaPipe, en paralelo y con cache por toma.

Cada toma se procesa una sola vez: el resultado se guarda en
cache/landmarks/<toma>.csv junto a una huella (nombre, tamano y fecha de cada
imagen + modelo de MediaPipe + umbral). Si la toma no cambia, se reutiliza.

Decisiones:
- Se guardan las 21 coordenadas x, y, z normalizadas a la imagen (lo que usa la
  CNN del enunciado) y ademas los 'world landmarks' en metros y la lateralidad
  (handedness) que estima MediaPipe, para poder estudiar otras normalizaciones y
  la invarianza mano izquierda / derecha sin volver a procesar las imagenes.
- Las imagenes sin mano detectada NO se descartan aqui: quedan con detectada=False
  para poder informar de la tasa de deteccion por participante y gesto.
- Mismo detector y mismos umbrales que el grabador y la demo (num_hands=1,
  confianza 0.5), para que lo que ve el modelo al entrenar sea lo que vera en vivo.
"""
import hashlib
import os
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import pandas as pd

from . import constantes as C
from . import utils
from .tomas import listar_imagenes

_DETECTOR = None


def _crear_detector(modelo_bytes, min_deteccion):
    utils.silenciar_tf()
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision
    opciones = vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_buffer=modelo_bytes),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=min_deteccion,
        min_tracking_confidence=0.5)
    return vision.HandLandmarker.create_from_options(opciones)


def _init_worker(modelo_bytes, min_deteccion):
    global _DETECTOR
    _DETECTOR = _crear_detector(modelo_bytes, min_deteccion)


def detectar(detector, imagen_bgr):
    import cv2
    import mediapipe as mp
    rgb = cv2.cvtColor(imagen_bgr, cv2.COLOR_BGR2RGB)
    return detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))


def resultado_a_fila(res, ancho, alto, brillo):
    fila = {'ancho': ancho, 'alto': alto, 'brillo': brillo, 'detectada': False,
            'handedness': None, 'handedness_score': np.nan, 'error': None}
    if res is not None and res.hand_landmarks:
        fila['detectada'] = True
        for i, p in enumerate(res.hand_landmarks[0]):
            fila['x%d' % i], fila['y%d' % i], fila['z%d' % i] = p.x, p.y, p.z
        if res.hand_world_landmarks:
            for i, p in enumerate(res.hand_world_landmarks[0]):
                fila['wx%d' % i], fila['wy%d' % i], fila['wz%d' % i] = p.x, p.y, p.z
        if res.handedness:
            fila['handedness'] = res.handedness[0][0].category_name
            fila['handedness_score'] = res.handedness[0][0].score
    return fila


def _procesar(fila_meta):
    ruta = Path(fila_meta['carpeta_toma']) / fila_meta['ruta_relativa']
    img = utils.leer_imagen(ruta)
    if img is None:
        fila = resultado_a_fila(None, np.nan, np.nan, np.nan)
        fila['error'] = 'imagen ilegible'
    else:
        alto, ancho = img.shape[:2]
        fila = resultado_a_fila(detectar(_DETECTOR, img), ancho, alto, float(img.mean()))
    return {**fila_meta, **fila}


def _huella(filas, modelo_bytes, min_deteccion):
    h = hashlib.sha256()
    h.update(hashlib.sha256(modelo_bytes).digest())
    h.update(str(min_deteccion).encode())
    for f in filas:
        st = (Path(f['carpeta_toma']) / f['ruta_relativa']).stat()
        h.update(('%s|%d|%d' % (f['ruta_relativa'], st.st_size, st.st_mtime_ns)).encode())
    return h.hexdigest()


def _normalizar_columnas(df):
    for c in C.COLS_LANDMARKS + C.COLS_WORLD:
        if c not in df.columns:
            df[c] = np.nan
    return df[C.COLS_META + C.COLS_RESULTADO + C.COLS_LANDMARKS + C.COLS_WORLD]


def leer_cache(ruta_csv):
    df = pd.read_csv(ruta_csv, dtype=C.DTYPES_TEXTO, keep_default_na=True)
    df['detectada'] = df['detectada'].astype(str).str.lower().eq('true')
    return df


def extraer_tomas(tomas, dir_cache=None, modelo_task=None, workers=None,
                  min_deteccion=0.5, forzar=False, log=print, avisos=None):
    """DataFrame con una fila por imagen de todas las tomas (cacheado por toma)."""
    dir_cache = dir_cache or C.DIR_CACHE              # se resuelven al llamar, no al importar
    modelo_task = modelo_task or C.MODELO_MEDIAPIPE
    avisos = avisos if avisos is not None else []
    workers = workers or utils.workers_por_defecto()
    modelo_bytes = Path(modelo_task).read_bytes()
    dir_lm = Path(dir_cache) / 'landmarks'
    dir_lm.mkdir(parents=True, exist_ok=True)

    partes, pendientes = [], []
    for toma in tomas:
        filas = listar_imagenes(toma, avisos)
        if not filas:
            avisos.append('la toma %s no tiene imagenes' % toma.nombre)
            continue
        csv = dir_lm / (toma.nombre + '.csv')
        meta = dir_lm / (toma.nombre + '.json')
        huella = _huella(filas, modelo_bytes, min_deteccion)
        if not forzar and csv.exists() and meta.exists() and utils.leer_json(meta).get('huella') == huella:
            df = leer_cache(csv)
            df['carpeta_toma'] = str(toma.carpeta)   # por si la toma se ha movido de sitio
            log('  [cache] %-34s %4d imagenes' % (toma.nombre, len(df)))
            partes.append(df)
        else:
            pendientes.append((toma, filas, csv, meta, huella))

    if pendientes:
        total = sum(len(p[1]) for p in pendientes)
        log('  extrayendo landmarks de %d imagenes (%d tomas) con %d procesos...' % (total, len(pendientes), workers))
        ctx = get_context('spawn')
        with ProcessPoolExecutor(max_workers=workers, mp_context=ctx,
                                 initializer=_init_worker, initargs=(modelo_bytes, min_deteccion)) as ex:
            for toma, filas, csv, meta, huella in pendientes:
                t0 = time.time()
                df = _normalizar_columnas(pd.DataFrame(list(ex.map(_procesar, filas, chunksize=4))))
                tmp = csv.with_name(csv.name + '.tmp')
                df.to_csv(tmp, index=False)
                os.replace(tmp, csv)
                utils.guardar_json({'huella': huella, 'toma': toma.nombre, 'imagenes': len(df),
                                    'detectadas': int(df['detectada'].sum()),
                                    'segundos': round(time.time() - t0, 1), 'fecha': utils.ahora()}, meta)
                log('  [nuevo] %-34s %4d imagenes, %4d con mano  (%.0f s)'
                    % (toma.nombre, len(df), df['detectada'].sum(), time.time() - t0))
                partes.append(df)

    if not partes:
        return _normalizar_columnas(pd.DataFrame(columns=C.COLS_META))
    df = pd.concat(partes, ignore_index=True)
    df['detectada'] = df['detectada'].astype(bool)
    return df
