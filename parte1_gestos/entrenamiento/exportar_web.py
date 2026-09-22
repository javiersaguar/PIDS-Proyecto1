"""Exporta el MLP de la parte 1 para el portal web: el reconocimiento de gestos corre en el navegador.

El portal (parte 4) reconoce los gestos con la cámara del propio navegador: MediaPipe Tasks para web saca los 21
puntos de la mano y este mismo MLP (normalización muñeca + escala + rotación, 96,5 % en LOPO) los clasifica. La
imagen no sale del navegador; a la plataforma solo llega la etiqueta y la confianza, como desde la demo de Windows.

Qué escribe:
  - parte4_frontend/web/public/gestos/modelo.json   pesos y sesgos de cada capa densa (se descarga al activar)
  - parte4_frontend/web/src/gestos/muestras.json     unas muestras reales del dataset con las probabilidades que da
                                                     este script, para que los tests del portal comprueben que el
                                                     modelo en TypeScript predice lo mismo

Solo necesita numpy y h5py (no Keras ni Torch): lee directamente el `.keras`, que es un zip con la arquitectura y
un HDF5 con los pesos. Antes de escribir, comprueba el modelo con los landmarks del dataset
(`datos_generados/landmarks_todas.csv.gz`, el mismo preprocesado que al entrenar).

Uso (desde la raíz del repositorio):
    uv run --no-project --with numpy --with h5py python parte1_gestos/entrenamiento/exportar_web.py
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import constantes as C, features as F  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
MODELO = RAIZ / 'parte1_gestos' / 'modelos' / 'plan_20260917-0042_mlp_muneca_escala_rot'
LANDMARKS = RAIZ / 'parte1_gestos' / 'datos_generados' / 'landmarks_todas.csv.gz'
DESTINO_MODELO = RAIZ / 'parte4_frontend' / 'web' / 'public' / 'gestos' / 'modelo.json'
DESTINO_MUESTRAS = RAIZ / 'parte4_frontend' / 'web' / 'src' / 'gestos' / 'muestras.json'
MUESTRAS_POR_CLASE = 4
DECIMALES = 7                     # float32 tiene unas 7 cifras significativas


def leer_modelo(carpeta: Path) -> dict:
    """Arquitectura y pesos del `.keras`, sin Keras: capas densas en orden, con su activación."""
    import h5py

    preprocesado = json.loads((carpeta / 'preprocesado.json').read_text(encoding='utf-8'))
    clases = json.loads((carpeta / 'etiquetas.json').read_text(encoding='utf-8'))['clases']
    ficha = json.loads((carpeta / 'ficha.json').read_text(encoding='utf-8'))
    if preprocesado['normalizacion'] != 'muneca_escala_rot' or preprocesado['forma_entrada'] != 'plano' or preprocesado['espejo']:
        raise SystemExit('el portal solo sabe preparar la entrada del MLP muneca_escala_rot, plano y sin espejo')
    with zipfile.ZipFile(carpeta / preprocesado['fichero_modelo']) as z:
        configuracion = json.loads(z.read('config.json'))
        pesos = h5py.File(io.BytesIO(z.read('model.weights.h5')), 'r')
        capas = []
        densas = [c for c in configuracion['config']['layers'] if c['class_name'] == 'Dense']
        nombres = sorted((n for n in pesos['layers'] if n.startswith('dense')), key=lambda n: (len(n), n))
        if len(densas) != len(nombres):
            raise SystemExit('la arquitectura no coincide con los pesos guardados')
        for capa, nombre in zip(densas, nombres, strict=True):
            kernel = np.asarray(pesos['layers'][nombre]['vars']['0'], dtype=np.float32)      # (entradas, salidas)
            sesgo = np.asarray(pesos['layers'][nombre]['vars']['1'], dtype=np.float32)
            capas.append({'activacion': capa['config']['activation'], 'kernel': kernel, 'sesgo': sesgo})
    lopo = ficha['metricas_referencia']['por_protocolo'][0]
    return {'clases': clases, 'capas': capas, 'normalizacion': preprocesado['normalizacion'],
            'accuracy_lopo': round(lopo['accuracy'], 4), 'experimento': ficha['metricas_referencia']['experimento']}


def predecir(modelo: dict, X: np.ndarray) -> np.ndarray:
    """Probabilidades (N, clases) con numpy: lo mismo que hará el portal en TypeScript."""
    h = X.astype(np.float32)
    for capa in modelo['capas']:
        h = h @ capa['kernel'] + capa['sesgo']
        if capa['activacion'] == 'relu':
            h = np.maximum(h, 0)
        elif capa['activacion'] == 'softmax':
            h = np.exp(h - h.max(axis=1, keepdims=True))
            h = h / h.sum(axis=1, keepdims=True)
        elif capa['activacion'] != 'linear':
            raise SystemExit(f'activación no soportada: {capa["activacion"]}')
    return h


def leer_landmarks(ruta: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """xy crudos (N, 21, 2), ancho, alto y clase de las imágenes con mano detectada."""
    import csv

    with gzip.open(ruta, 'rt', encoding='utf-8') as f:
        filas = [fila for fila in csv.DictReader(f) if fila['detectada'] == 'True']
    xy = np.array([[[float(fila[x]), float(fila[y])] for x, y in zip(C.COLS_X, C.COLS_Y, strict=True)] for fila in filas])
    ancho = np.array([float(fila['ancho']) for fila in filas])
    alto = np.array([float(fila['alto']) for fila in filas])
    return xy, ancho, alto, [fila['clase'] for fila in filas]


def entrada(xy: np.ndarray, ancho: np.ndarray, alto: np.ndarray) -> np.ndarray:
    ar = ancho / alto
    P = xy.copy()
    P[..., 0] = P[..., 0] * ar[:, None]
    return F.preparar_entrada(F.normalizar(P, ar, 'muneca_escala_rot'), 'plano')


def redondear(valores) -> list:
    return np.round(np.asarray(valores, dtype=np.float64), DECIMALES).tolist()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modelo', type=Path, default=MODELO)
    args = p.parse_args()

    modelo = leer_modelo(args.modelo)
    xy, ancho, alto, clases = leer_landmarks(LANDMARKS)
    probabilidades = predecir(modelo, entrada(xy, ancho, alto))
    aciertos = np.mean(np.array(modelo['clases'])[probabilidades.argmax(axis=1)] == np.array(clases))
    print(f'{len(clases)} imágenes con mano: {aciertos:.1%} de aciertos con numpy (el modelo final se entrenó con todas)')
    if aciertos < 0.9:
        raise SystemExit('los pesos no se han leído bien: el acierto debería rondar el 99 %')

    DESTINO_MODELO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO_MODELO.write_text(json.dumps({
        'origen': f'parte1_gestos/modelos/{args.modelo.name}',
        'experimento': modelo['experimento'],
        'accuracy_lopo': modelo['accuracy_lopo'],
        'normalizacion': modelo['normalizacion'],
        'clases': modelo['clases'],
        'capas': [{'activacion': c['activacion'], 'entradas': int(c['kernel'].shape[0]), 'salidas': int(c['kernel'].shape[1]),
                   'kernel': redondear(c['kernel'].reshape(-1)), 'sesgo': redondear(c['sesgo'])} for c in modelo['capas']],
    }, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'  {DESTINO_MODELO.relative_to(RAIZ)} · {DESTINO_MODELO.stat().st_size / 1024:.0f} KiB')

    rng = np.random.default_rng(0)
    elegidas = [int(i) for clase in modelo['clases']
                for i in rng.choice([j for j, c in enumerate(clases) if c == clase], MUESTRAS_POR_CLASE, replace=False)]
    DESTINO_MUESTRAS.parent.mkdir(parents=True, exist_ok=True)
    DESTINO_MUESTRAS.write_text(json.dumps([
        {'clase': clases[i], 'ancho': ancho[i], 'alto': alto[i], 'xy': redondear(xy[i]),
         'probabilidades': redondear(predecir(modelo, entrada(xy[i:i + 1], ancho[i:i + 1], alto[i:i + 1]))[0])}
        for i in elegidas], separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'  {DESTINO_MUESTRAS.relative_to(RAIZ)} · {len(elegidas)} muestras')
    return 0


if __name__ == '__main__':
    sys.exit(main())
