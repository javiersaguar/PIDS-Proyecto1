"""
### Carga histórica de viajes (PIDS · E3)

1. **subir_zonas**: tabla pública de zonas de la TLC → `s3://referencia/`
2. **subir_mes**: fichero Parquet del mes → `s3://crudo/historico/` (zona restringida).
   Con `muestra=true` se usa el CSV de 1000 viajes que ya subió la inicialización.
3. **spark_carga_historica**: Spark en modo *cluster* valida, archiva y publica agregados protegidos.
4. **comprobar_publicacion**: consulta la API de acceso (la misma puerta que usa el chatbot).

Parámetros: `mes` (2020-01 … 2020-12) y `muestra`.
"""
from __future__ import annotations

import os
from datetime import datetime

import boto3
import requests
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.sdk import DAG, Param, task
from botocore.exceptions import ClientError

URL_MES = 'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{mes}.parquet'
URL_ZONAS = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv'
RUTA_MUESTRA = 's3a://crudo/muestra/yellow_tripdata_2020_muestra.csv'


def _s3():
    return boto3.client('s3', endpoint_url=os.environ.get('PIDS_S3_ENDPOINT', 'http://s3:8333'),
                        region_name='us-east-1')


def _subir_desde_url(url: str, bucket: str, clave: str) -> bool:
    """Sube en streaming (sin pasar por disco). No repite si ya existe."""
    s3 = _s3()
    try:
        s3.head_object(Bucket=bucket, Key=clave)
        return False
    except ClientError:
        pass
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        r.raw.decode_content = True
        s3.upload_fileobj(r.raw, bucket, clave)
    return True


with DAG(
    dag_id='pids_carga_historica',
    description='Mes de viajes -> S3 restringido -> Spark (cluster) -> agregados protegidos en MongoDB',
    schedule=None,
    start_date=datetime(2026, 9, 1),
    catchup=False,
    max_active_runs=1,
    params={
        'mes': Param('2020-01', type='string', pattern=r'^2020-(0[1-9]|1[0-2])$', description='Mes de 2020'),
        'muestra': Param(False, type='boolean', description='Usar el CSV de muestra en lugar del mes completo'),
    },
    tags=['pids', 'parte2', 'historico'],
    doc_md=__doc__,
) as dag:

    @task
    def subir_zonas() -> None:
        _subir_desde_url(URL_ZONAS, 'referencia', 'taxi_zone_lookup.csv')

    @task
    def subir_mes(**contexto) -> str:
        params = contexto['params']
        if params['muestra']:
            return RUTA_MUESTRA
        clave = f'historico/yellow_tripdata_{params["mes"]}.parquet'
        _subir_desde_url(URL_MES.format(mes=params['mes']), 'crudo', clave)
        return f's3a://crudo/{clave}'

    carga = SparkSubmitOperator(
        task_id='spark_carga_historica',
        conn_id='spark_default',
        application='file:/opt/pids/pids-spark.jar',
        java_class='pids.CargaHistorica',
        name='pids-carga-historica',
        application_args=[
            "{{ ti.xcom_pull(task_ids='subir_mes') }}",
            "{{ 'muestra' if params.muestra else 'historico-' ~ params.mes }}",
        ],
        # El resto de la configuración (pasarela REST del máster, endpoint de S3, zona horaria…) viene
        # de parte2_plataforma/spark/conf/spark-defaults.conf, que la imagen de Airflow también lleva.
        conf={
            'spark.cores.max': '4',
            'spark.executor.cores': '2',
            'spark.executor.memory': '3g',
            'spark.driver.memory': '2g',
        },
    )

    @task
    def comprobar_publicacion(**contexto) -> dict:
        params = contexto['params']
        mes = params['mes']
        consulta = {'nivel': 'dia_barrio',
                    'desde': '2020-01-01T00:00:00' if params['muestra'] else f'{mes}-01T00:00:00',
                    'hasta': '2020-01-02T00:00:00' if params['muestra'] else f'{mes}-02T00:00:00'}
        r = requests.post(f'{os.environ["PIDS_ACCESO_URL"]}/consultas', json=consulta,
                          headers={'X-API-Key': os.environ['PIDS_ACCESO_CLAVE']}, timeout=30)
        r.raise_for_status()
        filas = r.json()['filas']
        if not filas:
            raise ValueError(f'No hay agregados publicados para {consulta["desde"][:10]}')
        return {'filas': len(filas), 'resultado': r.json()['resultado']}

    [subir_zonas(), subir_mes()] >> carga >> comprobar_publicacion()
