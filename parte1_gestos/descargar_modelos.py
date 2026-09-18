"""Descarga el modelo de MediaPipe que necesitan el grabador, el pipeline y la demo.

`hand_landmarker.task` pesa 7,8 MB y no se versiona: lo publica Google y se descarga cuando hace falta.
Se copia en las tres carpetas donde lo buscan los distintos programas.

Uso (en Windows, con el entorno de la parte 1):
    python parte1_gestos\\descargar_modelos.py
"""
from __future__ import annotations

import shutil
import sys
import urllib.request
from pathlib import Path

URL = ('https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/'
       'float16/1/hand_landmarker.task')
TAMANO_ESPERADO = 7_819_105
RAIZ = Path(__file__).resolve().parent
DESTINOS = [
    RAIZ / 'demo' / 'models' / 'hand_landmarker.task',
    RAIZ / 'kit_grabacion' / 'HAR_mediapipe' / 'models' / 'hand_landmarker.task',
]


def main() -> int:
    ya = next((d for d in DESTINOS if d.is_file() and d.stat().st_size == TAMANO_ESPERADO), None)
    if ya is None:
        destino = DESTINOS[0]
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f'Descargando hand_landmarker.task ({TAMANO_ESPERADO / 2**20:.1f} MB) de Google...')
        tmp = destino.with_suffix('.parcial')
        urllib.request.urlretrieve(URL, tmp)
        if tmp.stat().st_size != TAMANO_ESPERADO:
            print(f'Tamaño inesperado: {tmp.stat().st_size} bytes', file=sys.stderr)
            tmp.unlink(missing_ok=True)
            return 1
        tmp.replace(destino)
        ya = destino
        print(f'  guardado en {destino.relative_to(RAIZ)}')

    for destino in DESTINOS:
        if destino != ya and not (destino.is_file() and destino.stat().st_size == TAMANO_ESPERADO):
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ya, destino)
            print(f'  copiado a {destino.relative_to(RAIZ)}')
    print('Modelo de MediaPipe listo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
