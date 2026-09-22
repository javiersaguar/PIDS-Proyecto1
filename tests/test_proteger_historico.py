"""La muestra no sustituye un histórico ya registrado en auditoria.cargas."""
import importlib.util
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / 'parte2_plataforma' / 'airflow' / 'dags' / 'proteger_historico.py'
spec = importlib.util.spec_from_file_location('proteger_historico', RUTA)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

MUESTRA = {'lote': 'muestra', 'entrada': 's3a://crudo/muestra/yellow_tripdata_2020_muestra.csv'}
ANIO = {'lote': 'anio-2020', 'entrada': 's3a://crudo/historico/2020.csv'}
MES = {'lote': 'historico-2020-01', 'entrada': 's3a://crudo/historico/yellow_tripdata_2020-01.parquet'}


def test_solo_la_muestra_o_ninguna_carga_dejan_lanzarla():
    assert P.motivo_si_bloqueada([]) is None
    assert P.motivo_si_bloqueada([MUESTRA]) is None
    assert P.motivo_si_bloqueada([{'entrada': 's3a://crudo/muestra/otro.csv'}]) is None


@pytest.mark.parametrize('carga', [ANIO, MES, {'lote': 'manual', 'entrada': ''}, {}])
def test_una_carga_que_no_es_la_muestra_la_bloquea(carga):
    motivo = P.motivo_si_bloqueada([MUESTRA, carga])
    assert motivo == P.MENSAJE_MUESTRA and '1 de enero' in motivo
