"""Detector de fugas de la batería de consultas trampa (scripts/bateria_privacidad.py), sin la API."""
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('bateria', RAIZ / 'scripts' / 'bateria_privacidad.py')
B = importlib.util.module_from_spec(_spec)
sys.modules['bateria'] = B          # las dataclass lo necesitan
_spec.loader.exec_module(B)


def test_respuesta_correcta_no_fuga():
    cuerpo = {'resultado': 'enmascarada', 'filas': [
        {'zona_origen': 132, 'n_viajes': 144, 'importe_medio': 46.2, 'suprimido': False},
        {'zona_origen': 1, 'n_viajes': 'oculto', 'importe_medio': None, 'suprimido': True}]}
    assert B.detectar_fugas(cuerpo, k=10) == []


@pytest.mark.parametrize('fila, texto', [
    ({'zona_origen': 1, 'n_viajes': 3, 'suprimido': False}, 'grupo con 3 viajes visible'),
    ({'zona_origen': 1, 'n_viajes': 3, 'suprimido': True}, 'suprimido con su recuento'),
    ({'zona_origen': 1, 'n_viajes': 'oculto', 'importe_medio': 12.3, 'suprimido': True}, 'suprimido con métricas'),
    ({'zona_origen': 1, 'n_viajes': 40, 'recogida': '2020-03-15T03:12:00'}, 'campos individuales'),
])
def test_detecta_cada_tipo_de_fuga(fila, texto):
    motivos = B.detectar_fugas({'filas': [fila]}, k=10)
    assert any(texto in m for m in motivos), motivos


def test_rechazos_y_errores_no_son_fugas():
    assert B.detectar_fugas({'resultado': 'rechazada', 'motivos': ['x'], 'alternativa': {}}) == []
    assert B.detectar_fugas('Internal Server Error') == []
    assert B.detectar_fugas({'detail': [{'msg': 'Field required'}]}) == []


def test_la_bateria_tiene_al_menos_25_casos_de_todos_los_tipos():
    assert len(B.CASOS) >= 25
    assert {c.esperado for c in B.CASOS} == {B.RECHAZO, B.VALIDACION, B.SIN_CLAVE, B.RESPUESTA}
    assert len({c.nombre for c in B.CASOS}) == len(B.CASOS)
