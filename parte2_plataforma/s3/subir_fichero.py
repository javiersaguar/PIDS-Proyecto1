"""Sube un fichero de viajes a la zona restringida de S3 (bucket `crudo`), para que Spark lo cargue.

Es la ingesta manual: el equivalente a lo que hace el DAG de Airflow con los ficheros de la TLC, pero
para un fichero que ya se tiene descargado (por ejemplo la exportación completa de NYC Open Data).
Sube por partes, así que no carga el fichero en memoria.

Uso (desde el Makefile: `make subir-csv FICHERO=/ruta/al/fichero.csv`):
    python -m parte2_plataforma.s3.subir_fichero /entrada/2020_Yellow_Taxi_Trip_Data.csv
    python -m parte2_plataforma.s3.subir_fichero /entrada/fichero.csv --clave historico/2020_completo.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError


class Progreso:
    """Imprime el avance de la subida (la llama boto3 en varios hilos)."""

    def __init__(self, total: int):
        self.total = total
        self.hecho = 0
        self.ultimo_aviso = 0.0
        self.inicio = time.monotonic()
        self._lock = threading.Lock()
        self.interactivo = sys.stdout.isatty()

    def __call__(self, bytes_subidos: int) -> None:
        with self._lock:
            self.hecho += bytes_subidos
            porcentaje = 100 * self.hecho / self.total
            # en un terminal, cada 1 %; en un log (sin terminal), cada 10 %
            paso = 1 if self.interactivo else 10
            if porcentaje - self.ultimo_aviso < paso and self.hecho < self.total:
                return
            self.ultimo_aviso = porcentaje
            mb = self.hecho / 2**20
            velocidad = mb / max(0.1, time.monotonic() - self.inicio)
            fin = '' if self.interactivo else '\n'
            print(f'\r  {mb:8.0f} / {self.total / 2**20:.0f} MB  ({porcentaje:5.1f} %, '
                  f'{velocidad:.0f} MB/s)', end=fin, flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('fichero', type=Path)
    p.add_argument('--bucket', default='crudo')
    p.add_argument('--clave', default=None, help='ruta dentro del bucket (por defecto historico/<nombre>)')
    p.add_argument('--forzar', action='store_true', help='volver a subirlo aunque ya exista')
    args = p.parse_args()

    if not args.fichero.is_file():
        print(f'No existe el fichero {args.fichero}', file=sys.stderr)
        return 2
    clave = args.clave or f'historico/{args.fichero.name}'
    s3 = boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT', 'http://s3:8333'),
                      region_name='us-east-1')
    tamano = args.fichero.stat().st_size

    if not args.forzar:
        try:
            ya = s3.head_object(Bucket=args.bucket, Key=clave)
            if ya['ContentLength'] == tamano:
                print(f's3://{args.bucket}/{clave} ya está subido ({tamano / 2**30:.2f} GB)')
                print(f'Ruta para Spark: s3a://{args.bucket}/{clave}')
                return 0
            print('existe con otro tamaño: se vuelve a subir')
        except ClientError:
            pass

    print(f'Subiendo {args.fichero.name} ({tamano / 2**30:.2f} GB) a s3://{args.bucket}/{clave}')
    s3.upload_file(str(args.fichero), args.bucket, clave, Callback=Progreso(tamano),
                   Config=TransferConfig(multipart_chunksize=64 * 2**20, max_concurrency=4))
    print(f'\nListo. Ruta para Spark: s3a://{args.bucket}/{clave}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
