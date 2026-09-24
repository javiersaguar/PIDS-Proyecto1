"""Viajes sintéticos (`parte2_plataforma/simulador/sinteticos.py`).

Lo importante: todo lo generado tiene que pasar la validación real de la plataforma
(`comun.esquema`), la misma que aplican la captura y Spark. Si no, la simulación enviaría viajes que
acabarían en la carpeta de rechazos.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from parte2_plataforma.comun import esquema
from parte2_plataforma.simulador import sinteticos as S

RAIZ = Path(__file__).resolve().parents[1]
MUESTRA = RAIZ / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv'


@pytest.fixture(scope='module')
def generados() -> list[dict]:
    return S.generar(500, MUESTRA, semilla=7)[1]


def test_conserva_las_columnas_de_la_muestra(generados):
    with MUESTRA.open(newline='', encoding='utf-8-sig') as f:
        columnas = next(csv.reader(f))
    assert list(generados[0]) == columnas


def test_todos_los_viajes_son_validos(generados):
    df, _ = esquema.normalizar(pd.DataFrame(generados))
    validos, rechazados = esquema.validar(df)
    assert len(rechazados) == 0, rechazados[esquema.MOTIVOS].head().to_dict() if len(rechazados) else ''
    assert len(validos) == len(generados)


def test_las_fechas_caen_en_la_ventana_de_las_reglas(generados):
    desde, hasta = S.ventana()
    recogidas = [datetime.strptime(v[S.COLUMNA_RECOGIDA], S.FORMATO_FECHA) for v in generados]
    assert all(desde <= r < hasta for r in recogidas)
    assert recogidas == sorted(recogidas)                     # se envían en orden de recogida


def test_la_duracion_respeta_el_maximo(generados):
    maxima = timedelta(hours=float(S.reglas()['duracion_maxima_horas']))
    for viaje in generados:
        recogida = datetime.strptime(viaje[S.COLUMNA_RECOGIDA], S.FORMATO_FECHA)
        llegada = datetime.strptime(viaje[S.COLUMNA_LLEGADA], S.FORMATO_FECHA)
        assert timedelta(0) < llegada - recogida <= maxima


def test_el_importe_total_cuadra_con_sus_partes(generados):
    partes = ('fare_amount', 'extra', 'mta_tax', 'tip_amount', 'tolls_amount', 'improvement_surcharge',
              'congestion_surcharge')
    for viaje in generados[:50]:
        assert float(viaje['total_amount']) == pytest.approx(sum(float(viaje[p]) for p in partes), abs=0.02)


def test_la_semilla_repite_la_generacion():
    assert S.generar(20, MUESTRA, semilla=3)[1] == S.generar(20, MUESTRA, semilla=3)[1]
    assert S.generar(20, MUESTRA, semilla=3)[1] != S.generar(20, MUESTRA, semilla=4)[1]


def test_por_defecto_usa_los_dias_de_la_plantilla(generados):
    dias = {v[S.COLUMNA_RECOGIDA][:10] for v in generados}
    with MUESTRA.open(newline='', encoding='utf-8-sig') as f:
        dias_muestra = {fila[S.COLUMNA_RECOGIDA][:10] for fila in csv.DictReader(f)}
    assert dias <= dias_muestra


def test_reparte_por_el_tramo_pedido():
    desde, hasta = datetime(2020, 3, 1), datetime(2020, 3, 8)
    generados = S.generar(200, MUESTRA, semilla=1, desde=desde, hasta=hasta)[1]
    recogidas = [datetime.strptime(v[S.COLUMNA_RECOGIDA], S.FORMATO_FECHA) for v in generados]
    assert all(desde <= r < hasta for r in recogidas)
    assert len({r.date() for r in recogidas}) > 1             # no se amontonan en un solo día


def test_las_zonas_salen_de_la_plantilla_salvo_que_se_pidan_aleatorias():
    with MUESTRA.open(newline='', encoding='utf-8-sig') as f:
        zonas_muestra = {fila['PULocationID'] for fila in csv.DictReader(f)}
    copiadas = {v['PULocationID'] for v in S.generar(200, MUESTRA, semilla=2)[1]}
    assert copiadas <= zonas_muestra
    aleatorias = {v['PULocationID'] for v in S.generar(400, MUESTRA, semilla=2, zonas_aleatorias=True)[1]}
    assert len(aleatorias - zonas_muestra) > 0
    regs = S.reglas()
    assert all(int(regs['zona_minima']) <= int(z) <= int(regs['zona_maxima']) for z in aleatorias)


@pytest.mark.parametrize('filas', [0, -3, S.MAXIMO_FILAS + 1])
def test_rechaza_cantidades_imposibles(filas):
    with pytest.raises(ValueError):
        S.generar(filas, MUESTRA)


def test_rechaza_fechas_fuera_de_las_reglas():
    with pytest.raises(ValueError):
        S.generar(10, MUESTRA, desde=datetime(2019, 12, 1), hasta=datetime(2020, 1, 5))
    with pytest.raises(ValueError):
        S.generar(10, MUESTRA, desde=datetime(2020, 5, 5), hasta=datetime(2020, 5, 5))


def test_rechaza_una_plantilla_que_no_sirve(tmp_path):
    with pytest.raises(S.SinPlantillas):
        S.generar(10, tmp_path / 'no_existe.csv')
    vacio = tmp_path / 'vacio.csv'
    vacio.write_text('tpep_pickup_datetime,tpep_dropoff_datetime\n', encoding='utf-8')
    with pytest.raises(S.SinPlantillas):
        S.generar(10, vacio)
    otro = tmp_path / 'otro.csv'
    otro.write_text('a,b\n1,2\n', encoding='utf-8')
    with pytest.raises(S.SinPlantillas):
        S.generar(10, otro)


def test_una_plantilla_con_celdas_vacias_no_rompe(tmp_path):
    fichero = tmp_path / 'huecos.csv'
    with MUESTRA.open(newline='', encoding='utf-8-sig') as f:
        filas = list(csv.DictReader(f))[:20]
    for fila in filas:
        fila['tip_amount'] = fila['congestion_surcharge'] = ''
    S.escribir(fichero, list(filas[0]), filas)
    generados = S.generar(30, fichero, semilla=5)[1]
    assert all(v['tip_amount'] == '0.00' for v in generados)


def test_escribir_y_volver_a_leer(tmp_path):
    columnas, filas = S.generar(15, MUESTRA, semilla=9)
    destino = tmp_path / 'sub' / 'sinteticos.csv'
    S.escribir(destino, columnas, filas)
    with destino.open(newline='', encoding='utf-8') as f:
        leidas = list(csv.DictReader(f))
    assert leidas == filas


def test_cli_escribe_el_fichero(tmp_path, capsys):
    salida = tmp_path / 'sinteticos.csv'
    assert S.main([str(25), '--salida', str(salida), '--semilla', '1', '--plantilla', str(MUESTRA)]) == 0
    assert salida.is_file()
    assert 'semilla 1' in capsys.readouterr().out


def test_cli_avisa_del_error_sin_reventar(tmp_path, capsys):
    assert S.main(['10', '--plantilla', str(tmp_path / 'nada.csv'), '--salida', str(tmp_path / 'x.csv')]) == 1
    assert 'Error' in capsys.readouterr().err


def test_viaje_usa_la_hora_de_la_plantilla():
    plantilla = {S.COLUMNA_RECOGIDA: '01/01/2020 11:30:00 PM', 'trip_distance': '2', 'fare_amount': '10',
                 'passenger_count': '2', 'PULocationID': '138', 'DOLocationID': '230'}
    generado = S.viaje(plantilla, random.Random(0), datetime(2020, 6, 1), datetime(2020, 6, 30), S.reglas())
    recogida = datetime.strptime(generado[S.COLUMNA_RECOGIDA], S.FORMATO_FECHA)
    assert (recogida.hour, recogida.minute) == (23, 30)
    assert recogida.month == 6
