"""Simulador de tiempo real, configuración compartida y ficheros de despliegue."""
import ast
import json
import math
from pathlib import Path

import pandas as pd

from parte2_plataforma.comun import esquema as E
from parte2_plataforma.comun import privacidad as P
from parte2_plataforma.simulador import simulador as S

RAIZ = Path(__file__).resolve().parents[1]


def test_simulador_ordena_por_recogida_y_serializa():
    df = S.leer(RAIZ / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv', maximo=None)
    fechas = pd.to_datetime(df['tpep_pickup_datetime'], format='%m/%d/%Y %I:%M:%S %p')
    assert fechas.is_monotonic_increasing
    fila = S.a_json({'a': float('nan'), 'b': pd.Timestamp('2020-01-01 00:28:15'), 'c': pd.NA, 'd': 3})
    assert fila == {'a': None, 'b': '2020-01-01T00:28:15', 'c': None, 'd': 3}
    json.dumps(fila)


def test_configuraciones_coherentes():
    niveles = P.config()['niveles']
    assert set(P.config()['fuentes']) == {'historico', 'tiempo_real'}
    for nivel in niveles.values():
        assert nivel['tiempo'] in nivel['dimensiones'][0]
    # ninguna dimensión publicada es un campo individual
    publicadas = {d for n in niveles.values() for d in n['dimensiones']}
    assert not publicadas & set(P.config()['campos_individuales'])
    assert set(E.config()['obligatorias']) <= set(E.columnas())
    assert not math.isnan(E.config()['reglas']['distancia_maxima_millas'])


def test_dag_de_airflow_es_python_valido():
    fuente = (RAIZ / 'parte2_plataforma' / 'airflow' / 'dags' / 'pids_carga_historica.py').read_text(encoding='utf-8')
    arbol = ast.parse(fuente)
    assert any(isinstance(n, ast.With) for n in arbol.body)
    assert 'pids.CargaHistorica' in fuente


def test_dashboard_de_grafana_es_json_valido():
    ruta = RAIZ / 'parte2_plataforma' / 'observabilidad' / 'grafana' / 'dashboards' / 'plataforma.json'
    panel = json.loads(ruta.read_text(encoding='utf-8'))
    assert panel['uid'] == 'pids-plataforma'
    assert len({p['id'] for p in panel['panels']}) == len(panel['panels'])


def test_perfilado_de_la_muestra():
    import importlib.util
    spec = importlib.util.spec_from_file_location('perfilar', RAIZ / 'scripts' / 'perfilar_datos.py')
    perfilar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(perfilar)
    texto = perfilar.informe(RAIZ / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv')
    assert 'válidas **991**' in texto
    assert '| 1 (Tarjeta) |' in texto
    assert '| fecha_fuera_de_rango | 3 |' in texto
