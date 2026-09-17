"""Utilidades comunes: semillas, E/S robusta en Windows, versiones, tablas markdown."""
import contextlib
import io
import json
import os
import platform
import random
import sys
import time
import warnings
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np


BACKEND_POR_DEFECTO = 'torch'


def preparar_entorno(usar_gpu=True):
    """Variables de entorno ANTES de importar Keras, PyTorch o MediaPipe.

    - KERAS_BACKEND=torch: Keras 3 entrena con PyTorch. Es la unica forma de usar la GPU
      NVIDIA en Windows nativo (TensorFlow no tiene GPU en Windows desde la 2.11) y, en este
      portatil, Smart App Control bloquea las DLL de TensorFlow.
    - usar_gpu=False oculta la GPU a este proceso (CUDA_VISIBLE_DEVICES vacio): los procesos que
      solo usan scikit-learn o miden latencias en CPU no reservan memoria de la tarjeta.
    - CUBLAS_WORKSPACE_CONFIG es obligatorio para que cuBLAS sea determinista.
    """
    os.environ.setdefault('KERAS_BACKEND', BACKEND_POR_DEFECTO)
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    if not usar_gpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    os.environ.setdefault('GLOG_minloglevel', '2')
    os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
    os.environ.setdefault('PYTHONHASHSEED', '0')
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    silenciar_logs_tf()


silenciar_tf = preparar_entorno        # nombre antiguo


def configurar_torch(hilos=1, determinista=True):
    """Hilos de CPU y algoritmos deterministas de PyTorch (CPU y cuDNN)."""
    try:
        import torch
    except ImportError:
        return
    torch.set_num_threads(hilos)
    if determinista:
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def info_dispositivo():
    """Motor de Keras y dispositivo en el que va a entrenar este proceso."""
    info = {'backend': os.environ.get('KERAS_BACKEND', BACKEND_POR_DEFECTO), 'dispositivo': 'cpu',
            'gpu': None, 'vram_gb': None}
    try:
        import torch
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            info.update(dispositivo='cuda', gpu=torch.cuda.get_device_name(0),
                        vram_gb=round(p.total_memory / 1e9, 1))
    except ImportError:
        pass
    return info


def silenciar_logs_tf():
    """Avisos de Python de TF/Keras (reset_default_graph obsoleto, retracing de tf.function...)
    que no aportan nada y taparian el progreso. Llamar tambien DESPUES de importar TF."""
    import logging
    for nombre in ('tensorflow', 'absl', 'matplotlib.font_manager'):
        logging.getLogger(nombre).setLevel(logging.ERROR)
    try:
        import absl.logging
        absl.logging.set_verbosity(absl.logging.ERROR)
    except Exception:
        pass
    if 'tensorflow' in sys.modules:
        sys.modules['tensorflow'].get_logger().setLevel('ERROR')


def semilla_estable(*partes):
    """Entero determinista a partir de cualquier combinacion de valores.

    No se usa hash() de Python porque cambia entre ejecuciones (PYTHONHASHSEED).
    """
    return zlib.crc32('|'.join(str(p) for p in partes).encode('utf-8')) & 0x7FFFFFFF


def fijar_semillas(semilla):
    random.seed(semilla)
    np.random.seed(semilla % (2 ** 32))
    if 'keras' in sys.modules:
        import keras
        keras.utils.set_random_seed(semilla)


def leer_imagen(ruta):
    """cv2.imread no abre rutas con tildes o enes en Windows; imdecode+fromfile si."""
    import cv2
    try:
        datos = np.fromfile(str(ruta), dtype=np.uint8)
    except OSError:
        return None
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def guardar_json(obj, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_default), encoding='utf-8')
    os.replace(tmp, ruta)


def leer_json(ruta):
    return json.loads(Path(ruta).read_text(encoding='utf-8'))


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError('no serializable: %r' % type(o))


def ahora():
    return datetime.now().isoformat(timespec='seconds')


def marca_temporal():
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def versiones():
    v = {'python': platform.python_version(), 'sistema': platform.platform(),
         'procesador': platform.processor(), 'cpus_logicas': os.cpu_count()}
    for mod in ('numpy', 'pandas', 'sklearn', 'torch', 'keras', 'mediapipe', 'cv2', 'matplotlib', 'joblib'):
        try:
            v[mod] = __import__(mod).__version__
        except Exception:
            v[mod] = None
    v['keras_backend'] = os.environ.get('KERAS_BACKEND')
    try:
        import torch
        v['cuda'] = torch.version.cuda
        v['gpu'] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        v['cuda'] = v['gpu'] = None
    return v


@contextlib.contextmanager
def sin_salida():
    """Silencia prints de librerias (p. ej. el conversor de TFLite)."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


class Cronometro:
    def __enter__(self):
        self.inicio = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.segundos = time.perf_counter() - self.inicio


def tabla_markdown(df, formatos=None, indice=False):
    """DataFrame -> tabla markdown sin depender de 'tabulate'."""
    formatos = formatos or {}
    d = df.reset_index() if indice else df
    cols = [str(c) for c in d.columns]

    def fmt(col, v):
        if col in formatos and v is not None and not (isinstance(v, float) and np.isnan(v)):
            return formatos[col](v) if callable(formatos[col]) else formatos[col].format(v)
        if isinstance(v, float):
            return '' if np.isnan(v) else '%.4g' % v
        return str(v)

    filas = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' for _ in cols) + '|']
    for _, r in d.iterrows():
        filas.append('| ' + ' | '.join(fmt(c, r[c]) for c in d.columns) + ' |')
    return '\n'.join(filas)


def workers_por_defecto():
    n = os.cpu_count() or 4
    return max(1, min(12, n - 4))
