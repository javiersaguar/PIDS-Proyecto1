"""Coste de cada modelo: tamano en disco, parametros y latencia de inferencia.

Se mide en CPU, con UN solo hilo y batch 1, que es como funciona la demo (un fotograma
cada vez) y es mas representativo de una Raspberry Pi o un movil que la GPU del portatil.
Si TensorFlow esta disponible se mide ademas la version TFLite de las redes (float32 y con
cuantizacion de rango dinamico), que es el formato de despliegue en esos dispositivos. En
este portatil no lo esta (Smart App Control bloquea sus DLL), y entonces se deja anotado.
Tambien se mide el coste del extractor de MediaPipe, porque la latencia real de la demo es
extractor + clasificador.
"""
import importlib.util
import time
from pathlib import Path

import numpy as np

from . import utils

MOTIVO_SIN_TFLITE = 'TFLite requiere TensorFlow, que no esta instalado en este entorno'


def tflite_disponible():
    return importlib.util.find_spec('tensorflow') is not None


def medir_latencia(fn, repeticiones=300, calentamiento=30):
    for _ in range(calentamiento):
        fn()
    t = np.empty(repeticiones)
    for i in range(repeticiones):
        a = time.perf_counter()
        fn()
        t[i] = time.perf_counter() - a
    return {'mediana_ms': float(np.median(t) * 1e3), 'p90_ms': float(np.percentile(t, 90) * 1e3)}


def _tflite(modelo_keras, x1):
    import tensorflow as tf
    out = {}
    with utils.sin_salida():
        conv = tf.lite.TFLiteConverter.from_keras_model(modelo_keras)
        plano = conv.convert()
        conv = tf.lite.TFLiteConverter.from_keras_model(modelo_keras)
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
        cuant = conv.convert()
    out['tflite_bytes'] = len(plano)
    out['tflite_cuant_bytes'] = len(cuant)
    with utils.sin_salida():
        it = tf.lite.Interpreter(model_content=plano, num_threads=1)
    it.allocate_tensors()
    ent, sal = it.get_input_details()[0]['index'], it.get_output_details()[0]['index']
    x = np.asarray(x1, dtype=np.float32)

    def invocar():
        it.set_tensor(ent, x)
        it.invoke()
        it.get_tensor(sal)

    out['latencia_tflite_ms'] = medir_latencia(invocar, 1000, 100)['mediana_ms']
    return out, plano


def guardar_para_medir(modelo, x1, carpeta):
    """Durante el experimento solo se GUARDA el modelo: medir ahi seria medir con la CPU
    ocupada por los demas procesos de entrenamiento."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    modelo.guardar(carpeta)
    np.save(carpeta / 'x1.npy', np.asarray(x1))
    utils.guardar_json({'modelo': modelo.nombre, 'familia': modelo.familia, 'parametros': modelo.n_parametros()},
                       carpeta / 'info.json')


def medir_desde_disco(carpeta):
    """Carga un modelo guardado por guardar_para_medir y mide su coste (1 hilo, batch 1)."""
    carpeta = Path(carpeta)
    info = utils.leer_json(carpeta / 'info.json')
    x1 = np.load(carpeta / 'x1.npy')
    res = dict(info)
    if (carpeta / 'modelo.keras').exists():
        import keras
        ruta = carpeta / 'modelo.keras'
        m = keras.models.load_model(ruta, compile=False)
        res['bytes_disco'] = ruta.stat().st_size
        m(x1, training=False)
        res['latencia_ms'] = medir_latencia(lambda: m(x1, training=False))['mediana_ms']
        if not tflite_disponible():
            res['tflite_error'] = MOTIVO_SIN_TFLITE
        else:
            try:
                extra, _ = _tflite(m, x1)
                res.update(extra)
            except Exception as e:
                res['tflite_error'] = '%s: %s' % (type(e).__name__, str(e)[:200])
    else:
        import joblib
        ruta = carpeta / 'modelo.joblib'
        m = joblib.load(ruta)
        res['bytes_disco'] = ruta.stat().st_size
        res['latencia_ms'] = medir_latencia(lambda: m.predict_proba(x1))['mediana_ms']
    return res


def rendimiento_mediapipe(modelo_task, imagen_bgr, repeticiones=60):
    from .extraccion import _crear_detector, detectar
    det = _crear_detector(Path(modelo_task).read_bytes(), 0.5)
    r = medir_latencia(lambda: detectar(det, imagen_bgr), repeticiones, 10)
    alto, ancho = imagen_bgr.shape[:2]
    return {'modelo': 'extractor_mediapipe', 'familia': 'extractor', 'parametros': None,
            'bytes_disco': Path(modelo_task).stat().st_size, 'latencia_ms': r['mediana_ms'],
            'resolucion': '%dx%d' % (ancho, alto)}
