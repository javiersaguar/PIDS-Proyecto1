"""Descarga viajes de taxi amarillo de 2020 por meses, y la tabla de zonas.

El dataset completo tiene 24 648 499 viajes: no hace falta bajarlo entero para la prueba de concepto.

Fuentes:
  parquet  ficheros mensuales de la TLC (NYC Taxi & Limousine Commission), ~90 MB por mes. Rápido.
  api      API SODA de NYC Open Data (dataset kxp8-n2sj), paginada, en CSV. Más lenta, pero permite
           filtrar y es la misma fuente que el enlace del enunciado.

Uso:
    uv run python scripts/descargar_datos.py --meses 2020-01 2020-02
    uv run python scripts/descargar_datos.py --fuente api --meses 2020-01 --limite 100000
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / 'data' / 'crudo'
URL_PARQUET = 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{mes}.parquet'
URL_ZONAS = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv'
URL_API = 'https://data.cityofnewyork.us/resource/kxp8-n2sj.csv'
PAGINA_API = 50_000


def descargar(url: str, ruta: Path, params: dict | None = None) -> int:
    """Descarga en streaming a un fichero temporal y lo renombra al terminar (nunca deja ficheros a medias)."""
    tmp = ruta.with_suffix(ruta.suffix + '.parcial')
    with requests.get(url, params=params, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get('Content-Length', 0))
        hecho = 0
        with open(tmp, 'wb') as f:
            for trozo in r.iter_content(chunk_size=1 << 20):
                f.write(trozo)
                hecho += len(trozo)
                if total:
                    print(f'\r  {ruta.name}: {hecho / 2**20:6.1f} / {total / 2**20:.1f} MB', end='', flush=True)
    print()
    tmp.replace(ruta)
    return hecho


def mes_parquet(mes: str, forzar: bool) -> None:
    ruta = DESTINO / f'yellow_tripdata_{mes}.parquet'
    if ruta.exists() and not forzar:
        print(f'  ya existe {ruta.relative_to(RAIZ)} (usa --forzar para volver a bajarlo)')
        return
    descargar(URL_PARQUET.format(mes=mes), ruta)


def mes_api(mes: str, forzar: bool, limite: int | None) -> None:
    ruta = DESTINO / f'yellow_tripdata_{mes}_api.csv'
    if ruta.exists() and not forzar:
        print(f'  ya existe {ruta.relative_to(RAIZ)} (usa --forzar para volver a bajarlo)')
        return
    anio, m = map(int, mes.split('-'))
    siguiente = f'{anio + (m == 12)}-{(m % 12) + 1:02d}'
    donde = (f"tpep_pickup_datetime >= '{mes}-01T00:00:00' "
             f"AND tpep_pickup_datetime < '{siguiente}-01T00:00:00'")
    tmp = ruta.with_suffix('.csv.parcial')
    filas, offset = 0, 0
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        while limite is None or filas < limite:
            n = PAGINA_API if limite is None else min(PAGINA_API, limite - filas)
            params = {'$where': donde, '$order': 'tpep_pickup_datetime, :id', '$limit': n, '$offset': offset}
            r = requests.get(URL_API, params=params, timeout=120)
            r.raise_for_status()
            lineas = r.text.splitlines(keepends=True)
            cuerpo = lineas[1:]
            if offset == 0:
                f.write(lineas[0])
            if not cuerpo:
                break
            f.writelines(cuerpo)
            filas += len(cuerpo)
            offset += len(cuerpo)
            print(f'\r  {ruta.name}: {filas:,} filas', end='', flush=True)
            if len(cuerpo) < n:
                break
            time.sleep(0.2)          # sin token de aplicación la API limita el ritmo
    print()
    tmp.replace(ruta)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--meses', nargs='+', required=True, help='meses AAAA-MM de 2020')
    p.add_argument('--fuente', choices=['parquet', 'api'], default='parquet')
    p.add_argument('--limite', type=int, default=None, help='(api) máximo de filas por mes')
    p.add_argument('--forzar', action='store_true', help='volver a descargar aunque exista')
    args = p.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)
    zonas = DESTINO / 'taxi_zone_lookup.csv'
    if not zonas.exists():
        print('Tabla de zonas')
        descargar(URL_ZONAS, zonas)
    for mes in args.meses:
        if not (len(mes) == 7 and mes.startswith('2020-') and 1 <= int(mes[5:]) <= 12):
            print(f'mes no válido: {mes} (formato 2020-MM)', file=sys.stderr)
            return 2
        print(f'Mes {mes} ({args.fuente})')
        if args.fuente == 'parquet':
            mes_parquet(mes, args.forzar)
        else:
            mes_api(mes, args.forzar, args.limite)
    print(f'Datos en {DESTINO.relative_to(RAIZ)}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
