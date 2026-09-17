"""El esquema canónico y la validación, con la muestra real y con casos construidos a mano."""
from pathlib import Path

import pandas as pd
import pytest

from parte2_plataforma.comun import esquema as E

MUESTRA = Path(__file__).resolve().parents[1] / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv'


@pytest.fixture(scope='module')
def muestra():
    df, extra = E.normalizar(pd.read_csv(MUESTRA, dtype=str))
    return df, extra


def test_muestra_se_normaliza_sin_columnas_extra(muestra):
    df, extra = muestra
    assert extra == []
    assert list(df.columns) == E.columnas()
    assert len(df) == 999
    assert df['recogida'].notna().all() and df['llegada'].notna().all()


def test_muestra_rechaza_lo_esperado(muestra):
    df, _ = muestra
    validos, rechazados = E.validar(df)
    motivos = rechazados['motivos'].explode().value_counts()
    assert motivos['fecha_fuera_de_rango'] == 3        # tres viajes de diciembre de 2019
    assert motivos['importe_negativo'] == 4
    assert motivos['duracion_no_positiva'] == 1
    assert len(rechazados) == 8
    assert len(validos) + len(rechazados) == len(df)
    assert validos['recogida'].dt.year.eq(2020).all()


def test_formato_api_equivale_al_csv():
    csv = pd.DataFrame([{'VendorID': '1', 'tpep_pickup_datetime': '01/01/2020 12:28:15 AM',
                         'tpep_dropoff_datetime': '01/01/2020 12:33:03 AM', 'PULocationID': '238',
                         'DOLocationID': '239', 'trip_distance': '1.2', 'fare_amount': '6',
                         'total_amount': '11.27'}])
    api = pd.DataFrame([{'vendorid': '1', 'tpep_pickup_datetime': '2020-01-01T00:28:15.000',
                         'tpep_dropoff_datetime': '2020-01-01T00:33:03.000', 'pulocationid': '238',
                         'dolocationid': '239', 'trip_distance': '1.20', 'fare_amount': '6',
                         'total_amount': '11.27'}])
    a, _ = E.normalizar(csv)
    b, _ = E.normalizar(api)
    pd.testing.assert_frame_equal(a, b)


def test_columna_desconocida_se_informa_y_la_que_falta_invalida():
    df = pd.DataFrame([{'VendorID': 1, 'tpep_pickup_datetime': '2020-03-01T10:00:00',
                        'tpep_dropoff_datetime': '2020-03-01T10:10:00', 'PULocationID': 1,
                        'DOLocationID': 2, 'trip_distance': 1.0, 'fare_amount': 5,
                        'amount_total': 7.0}])        # nombre cambiado por el proveedor
    norm, extra = E.normalizar(df)
    assert extra == ['amount_total']
    _, rechazados = E.validar(norm)
    assert rechazados.iloc[0]['motivos'] == ['falta_campo_obligatorio']


@pytest.mark.parametrize('cambio, motivo', [
    ({'tpep_dropoff_datetime': '2020-03-01T09:00:00'}, 'duracion_no_positiva'),
    ({'tpep_dropoff_datetime': '2020-03-02T10:00:00'}, 'duracion_excesiva'),
    ({'trip_distance': -1}, 'distancia_fuera_de_rango'),
    ({'PULocationID': 999}, 'zona_desconocida'),
    ({'VendorID': 7}, 'vendor_desconocido'),
    ({'payment_type': 9}, 'tipo_pago_desconocido'),
    ({'store_and_fwd_flag': 'X'}, 'indicador_invalido'),
    ({'tpep_pickup_datetime': 'no es una fecha'}, 'falta_campo_obligatorio'),
])
def test_cada_regla(cambio, motivo):
    base = {'VendorID': 1, 'tpep_pickup_datetime': '2020-03-01T10:00:00',
            'tpep_dropoff_datetime': '2020-03-01T10:10:00', 'PULocationID': 1, 'DOLocationID': 2,
            'trip_distance': 1.0, 'fare_amount': 5, 'total_amount': 7.0, 'payment_type': 1,
            'store_and_fwd_flag': 'N'}
    norm, _ = E.normalizar(pd.DataFrame([{**base, **cambio}]))
    validos, rechazados = E.validar(norm)
    assert len(validos) == 0
    assert motivo in rechazados.iloc[0]['motivos']

    ok, _ = E.normalizar(pd.DataFrame([base]))
    assert len(E.validar(ok)[0]) == 1
