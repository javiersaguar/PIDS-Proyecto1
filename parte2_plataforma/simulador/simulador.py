"""Simulador de tiempo real: reenvía viajes de un fichero a la API de captura, como si llegaran en directo.

Uso:
    uv run python -m parte2_plataforma.simulador.simulador --fichero data/muestra/yellow_tripdata_2020_muestra.csv
    uv run python -m parte2_plataforma.simulador.simulador --fichero data/crudo/yellow_tripdata_2020-01.parquet \
        --ritmo 200 --maximo 50000

Los viajes se envían en orden de recogida (el procesado en tiempo real usa la hora del viaje).
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
    p.add_argument('--fichero', type=Path, required=True)
    p.add_argument('--url', default=os.environ.get('CAPTURA_URL', 'http://localhost:8001'))
    p.add_argument('--clave', default=os.environ.get('CAPTURA_CLAVE'))
    p.add_argument('--ritmo', type=float, default=50, help='viajes por segundo')
    p.add_argument('--lote', type=int, default=100, help='viajes por petición')
    p.add_argument('--maximo', type=int, default=None)
    args = p.parse_args()
    if not args.clave:
        print('Falta la clave de la API de captura (--clave o CAPTURA_CLAVE)', file=sys.stderr)
        return 2

    df = leer(args.fichero, args.maximo)
    nombre_lote = f'sim-{args.fichero.stem}-{datetime.now():%Y%m%d%H%M%S}'
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
