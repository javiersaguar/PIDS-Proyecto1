"""Lógica del ataque por diferencia (scripts/ataque_diferencia.py), sin la API."""
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('ataque', RAIZ / 'scripts' / 'ataque_diferencia.py')
A = importlib.util.module_from_spec(_spec)
sys.modules['ataque'] = A          # las dataclass lo necesitan
_spec.loader.exec_module(A)


@pytest.mark.parametrize('oculto, suprimidos, esperado', [
    (7, 1, (7, 7)),        # un único suprimido: su valor es la diferencia
    (10, 10, (1, 1)),      # diez suprimidos que suman diez: cada uno tiene un viaje
    (90, 10, (9, 9)),      # y si suman 90, cada uno tiene nueve
    (10, 2, (1, 9)),       # dos que suman diez: de 1 a 9 cada uno
    (17, 2, (8, 9)),       # dos que suman diecisiete: 8 o 9
    (25, 2, None),         # imposible con dos grupos de menos de 10: hay un complementario
    (0, 1, None),
])
def test_rango_por_grupo(oculto, suprimidos, esperado):
    assert A.rango_por_grupo(oculto, suprimidos, k=10) == esperado


def particion(total, visibles, suprimidos):
    return A.Particion(dia='2020-03-15', barrio='Queens', total=total, visibles=visibles, suprimidos=suprimidos)


@pytest.mark.parametrize('p, clase', [
    (particion(100, [100], 0), 'sin_suprimidos'),
    (particion(107, [100], 1), 'revelado'),
    (particion(111, [100], 11), 'revelado'),        # once grupos de un viaje
    (particion(117, [100], 2), 'acotado'),          # 8 o 9
    (particion(110, [100], 2), 'protegido'),        # de 1 a 9
    (particion(130, [100], 2), 'protegido'),        # un complementario rompe la cuenta del atacante
])
def test_clasificar(p, clase):
    assert A.clasificar(p, k=10) == clase


def test_resumir_cuenta_grupos_revelados():
    resumen = A.resumir([particion(107, [100], 1), particion(111, [100], 11), particion(110, [100], 2),
                         particion(100, [100], 0)], k=10)
    assert resumen['con_suprimidos'] == 3
    assert resumen['reveladas'] == 2 and resumen['grupos_revelados'] == 12
    assert resumen['pct_reveladas'] == pytest.approx(66.7)


def test_total_suprimido_se_reconstruye_con_los_flujos_si_todos_son_visibles():
    dia_barrio = [{'barrio_origen': 'Manhattan', 'n_viajes': 900, 'suprimido': False},
                  {'barrio_origen': 'Staten Island', 'n_viajes': 'oculto', 'suprimido': True},
                  {'barrio_origen': 'EWR', 'n_viajes': 'oculto', 'suprimido': True}]
    od = [{'barrio_origen': 'Staten Island', 'n_viajes': 12, 'suprimido': False},
          {'barrio_origen': 'Staten Island', 'n_viajes': 15, 'suprimido': False},
          {'barrio_origen': 'EWR', 'n_viajes': 11, 'suprimido': False},
          {'barrio_origen': 'EWR', 'n_viajes': 'oculto', 'suprimido': True}]
    publicados, reconstruidos = A.totales_del_dia(dia_barrio, od)
    assert publicados == {'Manhattan': 900}
    assert reconstruidos == {'Staten Island': 27}      # EWR no: tiene un flujo suprimido


def test_dias_de_muestra_reparte_el_anio():
    dias = A.dias_de_muestra(366)
    assert len(dias) == 366 and dias[0].month == 1 and dias[-1].month == 12
    assert len(set(dias)) == 366
