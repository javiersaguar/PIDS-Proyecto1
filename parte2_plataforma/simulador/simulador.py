"""Simulador de tiempo real: reenvía viajes de un fichero a la API de captura, como si llegaran en directo.

Uso:
    uv run python -m parte2_plataforma.simulador.simulador --fichero data/muestra/yellow_tripdata_2020_muestra.csv
    uv run python -m parte2_plataforma.simulador.simulador --fichero data/crudo/yellow_tripdata_2020-01.parquet \
        --ritmo 200 --maximo 50000
    uv run python -m parte2_plataforma.simulador.simulador --sinteticos 20000 --ritmo 200

Con `--sinteticos N` no se lee un fichero entero: se inventan N viajes a partir de la muestra
(`sinteticos.py`), para no quedarse en los 999 de siempre. Los viajes se envían en orden de recogida
(el procesado en tiempo real usa la hora del viaje).
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from parte2_plataforma.simulador import sinteticos as SINTETICOS


def leer(ruta: Path, maximo: int | None) -> pd.DataFrame:
    df = pd.read_parquet(ruta) if ruta.suffix == '.parquet' else pd.read_csv(ruta, dtype=str)
    columna = next((c for c in df.columns if c.lower() == 'tpep_pickup_datetime'), None)
    if columna is not None:
        orden = pd.to_datetime(df[columna], format='mixed', errors='coerce')
        df = df.iloc[orden.argsort(kind='stable')]
    return df.head(maximo) if maximo else df


def a_json(fila: dict) -> dict:
    salida = {}
    for k, v in fila.items():
        if isinstance(v, float) and math.isnan(v):
            v = None
        elif isinstance(v, (pd.Timestamp, datetime)):
            v = v.isoformat()
        elif v is pd.NA or v is pd.NaT:
            v = None
        elif hasattr(v, 'item'):
            v = v.item()
        salida[k] = v
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--fichero', type=Path, default=SINTETICOS.PLANTILLA_POR_DEFECTO,
                   help='fichero de viajes; con --sinteticos, la plantilla de la que salen')
    p.add_argument('--sinteticos', type=int, default=None,
                   help='genera este número de viajes a partir del fichero en vez de enviarlo entero')
    p.add_argument('--semilla', type=int, default=None, help='semilla de --sinteticos, para repetir la generación')
    p.add_argument('--desde', type=datetime.fromisoformat, default=None,
                   help='día de 2020 en el que caen los viajes (AAAA-MM-DD); sin --sinteticos, el fichero se mueve a '
                        'ese día. El tiempo real descarta lo anterior a la última hora que ya ha publicado')
    p.add_argument('--hasta', type=datetime.fromisoformat, default=None, help='día final, sin incluir')
    p.add_argument('--url', default=os.environ.get('CAPTURA_URL', 'http://localhost:8001'))
    p.add_argument('--clave', default=os.environ.get('CAPTURA_CLAVE'))
    p.add_argument('--ritmo', type=float, default=50, help='viajes por segundo')
    p.add_argument('--lote', type=int, default=100, help='viajes por petición')
    p.add_argument('--maximo', type=int, default=None)
    args = p.parse_args()
    if not args.clave:
        print('Falta la clave de la API de captura (--clave o CAPTURA_CLAVE)', file=sys.stderr)
        return 2

    if args.sinteticos:
        try:
            _, filas = SINTETICOS.generar(args.sinteticos, args.fichero, args.semilla, args.desde, args.hasta)
        except (SINTETICOS.SinPlantillas, ValueError) as error:
            print(f'Error: {error}', file=sys.stderr)
            return 2
        df = pd.DataFrame(filas)
        etiqueta = f'sinteticos-{args.sinteticos}'
    else:
        df = leer(args.fichero, args.maximo)
        if args.desde:                           # la muestra es del 1 de enero: se mueve al día pedido
            df = pd.DataFrame(SINTETICOS.desplazar_a_dia(df.to_dict('records'), args.desde.date()))
        etiqueta = args.fichero.stem
    nombre_lote = f'sim-{etiqueta}-{datetime.now():%Y%m%d%H%M%S}'
    sesion = requests.Session()
    sesion.headers['X-API-Key'] = args.clave
    enviados, inicio = 0, time.monotonic()
    for i in range(0, len(df), args.lote):
        trozo = [a_json(f) for f in df.iloc[i:i + args.lote].to_dict('records')]
        r = sesion.post(f'{args.url}/viajes', json={'lote': nombre_lote, 'viajes': trozo}, timeout=30)
        r.raise_for_status()
        enviados += len(trozo)
        espera = enviados / args.ritmo - (time.monotonic() - inicio)
        if espera > 0:
            time.sleep(espera)
        print(f'\r{enviados:,}/{len(df):,} viajes enviados', end='', flush=True)
    print(f'\nLote {nombre_lote} completado en {time.monotonic() - inicio:.0f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
