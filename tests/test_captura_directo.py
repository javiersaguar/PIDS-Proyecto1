"""Captura en directo (parte2_plataforma/simulador/directo.py): preparación, orden, punto de partida y reproducción."""
import asyncio
import csv
import gzip
from datetime import date, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from parte2_plataforma.simulador import directo as D

FORMATO = D.FORMATO_TLC


def parquet_de_prueba(ruta):
    recogidas = [datetime(2020, 12, 2, 10, 5), datetime(2020, 12, 1, 23, 59, 30), datetime(2020, 12, 1, 0, 0),
                 datetime(2003, 3, 26, 21, 7), datetime(2021, 1, 1, 0, 1), datetime(2020, 12, 1, 8, 30)]
    tabla = pa.table({
        'VendorID': [1, 2, 1, 2, 1, 2],
        'tpep_pickup_datetime': recogidas,
        'tpep_dropoff_datetime': [r + timedelta(minutes=12) for r in recogidas],
        'passenger_count': [1.0, None, 2.0, 1.0, 1.0, 3.0],
        'PULocationID': [132, 230, 161, 1, 2, 138],
        'fare_amount': [52.0, 7.5, 9.0, 1.0, 1.0, 44.5],
        'airport_fee': [None] * 6,
    })
    pq.write_table(tabla, ruta)
    return ruta


def escribir_dia(carpeta, dia: str, recogidas: list[str]):
    carpeta.mkdir(parents=True, exist_ok=True)
    with gzip.open(carpeta / f'{dia}.csv.gz', 'wt', newline='', encoding='utf-8') as f:
        escritor = csv.writer(f)
        escritor.writerow(['VendorID', 'tpep_pickup_datetime', 'PULocationID'])
        for i, texto in enumerate(recogidas):
            escritor.writerow([i, texto, 132])


def test_preparar_parte_por_dia_ordena_y_deja_fuera_lo_que_no_es_del_mes(tmp_path):
    cuentas = D.preparar(parquet_de_prueba(tmp_path / 'mes.parquet'), tmp_path / 'directo', '2020-12')
    assert cuentas == {'2020-12-01': 3, '2020-12-02': 1}
    assert D.dias_disponibles(tmp_path / 'directo') == [date(2020, 12, 1), date(2020, 12, 2)]
    with gzip.open(tmp_path / 'directo' / '2020-12-01.csv.gz', 'rt', encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    assert [f['tpep_pickup_datetime'] for f in filas] == [
        '12/01/2020 12:00:00 AM', '12/01/2020 08:30:00 AM', '12/01/2020 11:59:30 PM']
    assert filas[0]['passenger_count'] == '2' and filas[2]['passenger_count'] == ''   # 2.0 -> 2, nulo -> vacío
    assert 'airport_fee' not in filas[0]                                             # no existía en 2020
    for fila in filas:                                                               # el formato de la validación
        datetime.strptime(fila['tpep_dropoff_datetime'], FORMATO)


def test_viajes_desde_recorre_los_dias_en_orden_desde_el_minuto_pedido(tmp_path):
    escribir_dia(tmp_path, '2020-12-01', ['12/01/2020 10:00:00 PM', '12/01/2020 11:30:00 PM'])
    escribir_dia(tmp_path, '2020-12-02', ['12/02/2020 12:15:00 AM', '12/02/2020 01:00:00 AM'])
    (tmp_path / 'notas.csv.gz').write_bytes(b'')                                     # no es un día: se ignora
    viajes = list(D.viajes_desde(tmp_path, datetime(2020, 12, 1, 23, 0)))
    assert [v['tpep_pickup_datetime'] for v in viajes] == [
        '12/01/2020 11:30:00 PM', '12/02/2020 12:15:00 AM', '12/02/2020 01:00:00 AM']
    assert viajes[0]['VendorID'] == '1'


def test_punto_de_partida_sigue_donde_se_quedo_y_nunca_vuelve_atras():
    dias = [date(2020, 12, 1), date(2020, 12, 2)]
    assert D.punto_de_partida(dias, None) == datetime(2020, 12, 1)
    assert D.punto_de_partida(dias, datetime(2020, 12, 1, 5)) == datetime(2020, 12, 1, 6)
    # la hora a medias es de esta captura: se sigue en el minuto exacto, sin huecos ni repetidos
    assert D.punto_de_partida(dias, datetime(2020, 12, 1, 5), datetime(2020, 12, 1, 5, 40)) == datetime(2020, 12, 1, 5, 40)
    # Spark tiene algo más reciente que el reloj (otra captura, pruebas): manda lo publicado
    assert D.punto_de_partida(dias, datetime(2020, 12, 1, 9), datetime(2020, 12, 1, 5, 40)) == datetime(2020, 12, 1, 10)
    with pytest.raises(D.SinDatos, match='tiempo-real-reiniciar'):
        D.punto_de_partida(dias, datetime(2020, 12, 2, 23))                  # ya está todo
    with pytest.raises(D.SinDatos, match='latencia|tiempo-real-reiniciar'):
        D.punto_de_partida(dias, datetime(2020, 12, 31, 20))                 # p. ej. tras `make latencia`
    with pytest.raises(D.SinDatos, match='captura-preparar'):
        D.punto_de_partida([], None)


class RelojFalso:
    """El tiempo real avanza un segundo por cada `sleep` de la reproducción."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_reproducir_envia_cada_viaje_cuando_el_reloj_simulado_lo_alcanza(tmp_path, monkeypatch):
    escribir_dia(tmp_path, '2020-12-01', [f'12/01/2020 12:{m:02d}:00 AM' for m in range(0, 30, 2)]
                 + ['12/01/2020 01:00:00 AM'])
    reloj = RelojFalso()
    enviados: list[tuple[float, list[str]]] = []

    async def enviar(viajes):
        enviados.append((reloj.t, [v['tpep_pickup_datetime'][11:16] for v in viajes]))

    async def dormir(segundos):
        reloj.t += segundos

    monkeypatch.setattr(D.asyncio, 'sleep', dormir)
    monkeypatch.setattr(D, 'MAX_LOTE', 4)
    progreso = asyncio.run(D.reproducir(enviar, tmp_path, datetime(2020, 12, 1), velocidad=600, reloj_real=reloj))
    # a ×600 cada segundo real son 10 minutos de 2020: 00:00 enseguida, luego tandas de 5 viajes (lotes de 4 + 1)
    assert enviados[0] == (0.0, ['12:00'])
    assert [len(v) for _, v in enviados] == [1, 4, 1, 4, 1, 4, 1]
    assert enviados[-1] == (6.0, ['01:00'])
    assert progreso.enviados == 16 and progreso.reloj == datetime(2020, 12, 1, 1, 0)
    todos = [h for _, v in enviados for h in v]                                  # el orden de recogida se conserva
    assert todos == [f'12:{m:02d}' for m in range(0, 30, 2)] + ['01:00']


def test_reproducir_sin_nada_desde_ese_punto_avisa(tmp_path):
    escribir_dia(tmp_path, '2020-12-01', ['12/01/2020 12:00:00 AM'])

    async def enviar(viajes):
        raise AssertionError('no debería enviar nada')

    with pytest.raises(D.SinDatos):
        asyncio.run(D.reproducir(enviar, tmp_path, datetime(2020, 12, 2), velocidad=60))


def test_ultima_hora_publicada_busca_el_ultimo_dia_y_despues_la_ultima_hora():
    publicadas = {datetime(2020, 12, 1, h) for h in range(0, 8)} | {datetime(2020, 12, 2, 3)}
    pedidas = []

    async def consultar(consulta):
        pedidas.append(consulta['nivel'])
        desde, hasta = (datetime.fromisoformat(consulta[c]) for c in ('desde', 'hasta'))
        return [{'hora': h} for h in publicadas if desde <= h < hasta]

    dias = [date(2020, 12, d) for d in (1, 2, 3)]
    assert asyncio.run(D.ultima_hora_publicada(consultar, dias)) == datetime(2020, 12, 2, 3)
    # el 3 no tiene nada; el 2 sí: se mira hora a hora desde las 23 hasta dar con las 03
    assert pedidas == ['dia_barrio', 'dia_barrio'] + ['hora_zona'] * 21
    publicadas.clear()
    assert asyncio.run(D.ultima_hora_publicada(consultar, dias)) is None


@pytest.mark.skipif(not D.dias_disponibles(), reason='sin datos preparados (make captura-preparar)')
def test_los_datos_preparados_son_de_un_mes_de_2020_y_estan_ordenados():
    dias = D.dias_disponibles()
    assert all(d.year == 2020 for d in dias)
    viajes = [v for _, v in zip(range(2000), D.viajes_desde(D.CARPETA, datetime.combine(dias[0], datetime.min.time())))]
    recogidas = [D.recogida(v) for v in viajes]
    assert recogidas == sorted(recogidas) and recogidas[0].date() == dias[0]
