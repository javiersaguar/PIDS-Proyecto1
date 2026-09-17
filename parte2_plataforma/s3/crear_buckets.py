"""Inicializa el almacenamiento S3 (se ejecuta una vez al levantar la plataforma, con la identidad admin).

Buckets:
  crudo       zona restringida: viajes individuales (histórico, válidos, rechazados). Solo Spark e ingesta.
  referencia  datos públicos de referencia (tabla de zonas de la TLC).

Minimización (E3): los rechazos y el archivo de tiempo real caducan solos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3
import requests
from botocore.exceptions import ClientError

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv'
URL_ZONAS = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv'
BUCKETS = ['crudo', 'referencia']
CADUCIDAD = [('rechazos/', 30), ('validos/tiempo_real/', 90)]


def cliente():
    return boto3.client('s3', endpoint_url=os.environ.get('S3_ENDPOINT', 'http://s3:8333'),
                        region_name='us-east-1')


def existe(s3, bucket: str, clave: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=clave)
        return True
    except ClientError:
        return False


def main() -> int:
    s3 = cliente()
    existentes = {b['Name'] for b in s3.list_buckets().get('Buckets', [])}
    for bucket in BUCKETS:
        if bucket not in existentes:
            s3.create_bucket(Bucket=bucket)
            print(f'bucket creado: {bucket}')

    try:
        s3.put_bucket_lifecycle_configuration(Bucket='crudo', LifecycleConfiguration={'Rules': [
            {'ID': f'caduca-{prefijo.strip("/").replace("/", "-")}', 'Status': 'Enabled',
             'Filter': {'Prefix': prefijo}, 'Expiration': {'Days': dias}}
            for prefijo, dias in CADUCIDAD]})
        print('caducidad configurada en crudo: ' + ', '.join(f'{p} {d} días' for p, d in CADUCIDAD))
    except ClientError as e:
        print(f'aviso: no se pudo configurar la caducidad ({e})')

    if not existe(s3, 'crudo', 'muestra/yellow_tripdata_2020_muestra.csv'):
        s3.upload_file(str(MUESTRA), 'crudo', 'muestra/yellow_tripdata_2020_muestra.csv')
        print('muestra subida a s3://crudo/muestra/')

    if not existe(s3, 'referencia', 'taxi_zone_lookup.csv'):
        try:
            r = requests.get(URL_ZONAS, timeout=60)
            r.raise_for_status()
            s3.put_object(Bucket='referencia', Key='taxi_zone_lookup.csv', Body=r.content)
            print('tabla de zonas subida a s3://referencia/')
        except requests.RequestException as e:
            print(f'aviso: no se pudo descargar la tabla de zonas ({e}); la subirá el DAG de Airflow')
    return 0


if __name__ == '__main__':
    sys.exit(main())
