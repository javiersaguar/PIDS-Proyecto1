"""Reglas propias de privacidad: cada consulta peligrosa se rechaza con una alternativa válida."""
from datetime import datetime

import pytest

from parte2_plataforma.comun import privacidad as P


def consulta(**cambios):
    base = dict(nivel='hora_zona', desde=datetime(2020, 1, 15, 8), hasta=datetime(2020, 1, 15, 12),
                metricas=['n_viajes', 'importe_medio'], zona_origen=138)
    return P.Consulta(**{**base, **cambios})


def test_consulta_bien_formada_se_permite():
    assert P.evaluar(consulta()).resultado == P.Resultado.PERMITIDA


@pytest.mark.parametrize('cambios, texto', [
    (dict(campos_extra=['recogida']), 'campos individuales'),
    (dict(campos_extra=['matricula']), 'campos individuales'),
    (dict(metricas=['importe_total']), 'métricas no publicadas'),
    (dict(desde=datetime(2020, 1, 15, 3, 12), hasta=datetime(2020, 1, 15, 3, 13)), 'granularidad'),
    (dict(desde=datetime(2020, 1, 1), hasta=datetime(2020, 3, 1)), 'rango máximo'),
    (dict(barrio_destino='Queens'), 'destino'),
    (dict(nivel='dia_barrio', desde=datetime(2020, 1, 15), hasta=datetime(2020, 1, 16)), 'no tiene zona'),
])
def test_consultas_peligrosas_se_rechazan(cambios, texto):
    decision = P.evaluar(consulta(**cambios))
    assert decision.resultado == P.Resultado.RECHAZADA
    assert any(texto in m for m in decision.motivos)


@pytest.mark.parametrize('cambios', [
    dict(campos_extra=['recogida', 'zona_destino']),
    dict(desde=datetime(2020, 1, 15, 3, 12), hasta=datetime(2020, 1, 15, 3, 13)),
    dict(desde=datetime(2020, 1, 1), hasta=datetime(2020, 6, 1)),
    dict(barrio_destino='Queens', desde=datetime(2020, 1, 15, 3, 12), hasta=datetime(2020, 1, 15, 4)),
    dict(nivel='dia_barrio', barrio_origen='Manhattan'),
    dict(hasta=datetime(2020, 1, 15, 7)),
])
def test_la_alternativa_siempre_se_permite(cambios):
    decision = P.evaluar(consulta(**cambios))
    assert decision.resultado == P.Resultado.RECHAZADA
    assert decision.alternativa is not None
    assert P.evaluar(decision.alternativa).resultado == P.Resultado.PERMITIDA


def test_alternativa_alinea_a_la_hora_completa():
    alt = P.evaluar(consulta(desde=datetime(2020, 1, 15, 3, 12), hasta=datetime(2020, 1, 15, 3, 13))).alternativa
    assert (alt.desde, alt.hasta) == (datetime(2020, 1, 15, 3), datetime(2020, 1, 15, 4))


def test_enmascarar_oculta_cifras_y_no_da_totales():
    filas = [
        {'_id': 'a', 'zona_origen': 1, 'n_viajes': 25, 'importe_medio': 12.5, 'suprimido': False},
        {'_id': 'b', 'zona_origen': 2, 'n_viajes': None, 'importe_medio': None, 'suprimido': True},
    ]
    salida, ocultas = P.enmascarar(filas, ['importe_medio'])
    assert ocultas == 1
    assert '_id' not in salida[0]
    assert salida[1]['n_viajes'] == 'oculto'
    assert salida[1]['importe_medio'] is None
    assert P.resultado_final(ocultas) == P.Resultado.ENMASCARADA


def test_coleccion_segun_fuente():
    assert P.coleccion(consulta()) == 'viajes_hora_zona'
    assert P.coleccion(consulta(fuente='tiempo_real')) == 'tr_viajes_hora_zona'


def test_barrio_desconocido_se_rechaza_con_alternativa_sin_filtro():
    peticion = consulta(nivel="dia_barrio", zona_origen=None, desde=datetime(2020, 1, 1),
                        hasta=datetime(2020, 1, 2), barrio_origen="[Manhattan, Brooklyn]")
    decision = P.evaluar(peticion)
    assert decision.resultado == P.Resultado.RECHAZADA
    assert any("barrio_origen desconocido" in m for m in decision.motivos)
    assert decision.alternativa.barrio_origen is None
    assert P.evaluar(decision.alternativa).resultado == P.Resultado.PERMITIDA


def test_barrio_vacio_equivale_a_sin_filtro():
    peticion = consulta(nivel="dia_barrio", zona_origen=None, desde=datetime(2020, 1, 1),
                        hasta=datetime(2020, 1, 2), barrio_origen="  ", barrio_destino="")
    assert peticion.barrio_origen is None and peticion.barrio_destino is None
    assert P.evaluar(peticion).resultado == P.Resultado.PERMITIDA


def test_metricas_vacias_usan_el_numero_de_viajes():
    assert consulta(metricas=[]).metricas == ["n_viajes"]


def test_mensaje_de_granularidad_concuerda():
    dia = P.evaluar(consulta(nivel="dia_barrio", zona_origen=None, desde=datetime(2020, 1, 1, 5),
                             hasta=datetime(2020, 1, 1, 9)))
    assert any("de un día completo" in m for m in dia.motivos)
    hora = P.evaluar(consulta(desde=datetime(2020, 1, 1, 5, 30), hasta=datetime(2020, 1, 1, 9)))
    assert any("de una hora completa" in m for m in hora.motivos)


@pytest.mark.parametrize('metricas, esperado', [
    ('["n_viajes", "importe_medio"]', ['n_viajes', 'importe_medio']),
    ('n_viajes, propina_media', ['n_viajes', 'propina_media']),
    ('n_viajes', ['n_viajes']),
    ('', ['n_viajes']),
    ([], ['n_viajes']),
])
def test_metricas_mal_formadas_por_el_llm_se_normalizan(metricas, esperado):
    """La API acepta la chapuza de formato, pero sigue validando contra las métricas publicadas."""
    peticion = consulta(metricas=metricas)
    assert peticion.metricas == esperado
    assert P.evaluar(peticion).resultado == P.Resultado.PERMITIDA


@pytest.mark.parametrize('zona', ['', 'null', None])
def test_zona_vacia_equivale_a_sin_filtro(zona):
    assert consulta(nivel='dia_barrio', desde=datetime(2020, 1, 1), hasta=datetime(2020, 1, 2),
                    zona_origen=zona).zona_origen is None


def test_campos_extra_como_texto_siguen_rechazandose():
    decision = P.evaluar(consulta(campos_extra='["recogida"]'))
    assert decision.resultado == P.Resultado.RECHAZADA
    assert any('campos individuales' in m for m in decision.motivos)
