"""Guardia de salida del chatbot RAG (parte3_chatbot_rag/salida.py): qué puede viajar al proveedor y qué no."""
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'parte3_chatbot_rag'))
sys.path.insert(0, str(RAIZ / 'parte3_chatbot'))

import salida as S  # noqa: E402


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'clave-secreta-del-proveedor')
    monkeypatch.setenv('ACCESO_CLAVE', 'clave-secreta-de-acceso')
    monkeypatch.delenv('CAPTURA_CLAVE', raising=False)


def _mensajes_normales() -> list:
    return [
        SystemMessage('Eres el asistente. No existen datos de viajes, conductores ni vehículos concretos. '
                      'Un día: desde 2020-03-03T00:00:00 hasta 2020-03-04T00:00:00.'),
        HumanMessage('¿Cuál fue la propina media en Manhattan el 3 de marzo?'),
        AIMessage('', tool_calls=[{'name': 'consultar_viajes', 'id': 'c1',
                                   'args': {'nivel': 'dia_barrio', 'desde': '2020-03-03T00:00:00',
                                            'hasta': '2020-03-04T00:00:00', 'barrio_origen': 'Manhattan',
                                            'metricas': ['propina_media']}}]),
        ToolMessage('{"resultado": "permitida", "filas": [{"dia": "2020-03-03", "barrio_origen": "Manhattan", '
                    '"n_viajes": 203866, "propina_media": 2.07, "importe_medio": 17.3}], '
                    '"resumen": {"total_viajes": 203866, "propina_media_conjunta": 2.07}}', tool_call_id='c1'),
        ToolMessage('[{"id": 132, "nombre": "JFK Airport", "barrio": "Queens"}]', tool_call_id='c2'),
    ]


def test_los_mensajes_normales_salen_tal_cual():
    mensajes = _mensajes_normales()
    assert S.GuardiaSalida().revisar(mensajes) is mensajes


def test_las_metricas_agregadas_y_las_zonas_no_son_campos_individuales():
    # propina_media e importe_medio no son "propina" ni "importe_total"; el id de una zona no es el id de un viaje
    assert S.motivos_de('{"propina_media": 2.07, "importe_medio": 17.3, "id": 132, "n_viajes": 203866}') == []
    assert S.motivos_de('La tarifa media y la propina media suben en Manhattan') == []
    assert S.motivos_de('no hay datos de conductores: matrícula, pasajeros o tarifa') == []


@pytest.mark.parametrize('texto, campo', [
    ('{"recogida": "2020-01-15T08:23:41", "zona_origen": 132}', 'recogida'),
    ("{'matricula': 'T123456C', 'tarifa': 12.5}", 'matricula'),
    ('importe_total=45.3 pasajeros=2', 'importe_total'),
    ('conductor: Juan Pérez', 'conductor'),
    ('"zona_destino": 230', 'zona_destino'),
])
def test_un_campo_individual_con_valor_no_sale(texto, campo):
    motivos = S.motivos_de(texto)
    assert motivos and campo in motivos[0]
    with pytest.raises(S.FugaSalida) as e:
        S.GuardiaSalida().revisar([HumanMessage('hola'), ToolMessage(texto, tool_call_id='x')])
    assert 'mensaje 2 (tool)' in str(e.value) and campo in str(e.value)


def test_el_motivo_no_revela_el_dato():
    with pytest.raises(S.FugaSalida) as e:
        S.GuardiaSalida().revisar([ToolMessage('{"matricula": "T123456C", "recogida": "2020-01-15T08:23:41"}',
                                               tool_call_id='x')])
    assert 'T123456C' not in str(e.value) and '08:23' not in str(e.value)


def test_un_campo_nulo_o_vacio_no_cuenta():
    assert S.motivos_de('{"recogida": null, "matricula": "", "conductor": None}') == []


def test_instantes_exactos():
    assert S.motivos_de('desde 2020-01-15T08:00:00 hasta 2020-01-15T12:00:00 y la hora 2020-01-15 09:00') == []
    assert S.motivos_de('recogido a las 2020-01-15T08:23:41')                       # minutos
    assert S.motivos_de('llegada 2020-01-15 08:00:07')                                # segundos
    assert S.motivos_de('{"hora": "2020-01-15T03:12"}')


@pytest.mark.parametrize('texto', [
    'mi clave es sk-hke_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    'X-API-Key: una-clave-cualquiera',
    'Authorization = Bearer abcdef',
    'la clave de acceso es clave-secreta-de-acceso',          # el valor real del entorno
    'LLM: clave-secreta-del-proveedor',
])
def test_las_claves_no_salen(texto):
    assert any('clave de acceso' in m for m in S.motivos_de(texto))


def test_las_llamadas_a_herramientas_del_asistente_tambien_se_revisan():
    mensaje = AIMessage('', tool_calls=[{'name': 'consultar_viajes', 'id': 'c1',
                                         'args': {'campos_extra': ['recogida'], 'matricula': 'T123456C'}}])
    with pytest.raises(S.FugaSalida):
        S.GuardiaSalida().revisar([mensaje])


def test_una_conversacion_desmesurada_no_sale():
    guardia = S.GuardiaSalida(max_caracteres=100)
    with pytest.raises(S.FugaSalida) as e:
        guardia.revisar([HumanMessage('a' * 60), HumanMessage('b' * 60)])
    assert 'conversación nueva' in str(e.value)
    assert guardia.revisar([HumanMessage('a' * 60)])


def test_registrar_acumula_tokens_sin_guardar_contenido():
    guardia = S.GuardiaSalida()
    guardia.registrar(AIMessage('listo', usage_metadata={'input_tokens': 39, 'output_tokens': 15, 'total_tokens': 54,
                                                          'output_token_details': {'reasoning': 12}}))
    guardia.registrar(AIMessage('otra', usage_metadata={'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}))
    guardia.registrar(AIMessage('sin uso'))
    assert guardia.llamadas == 3
    assert guardia.tokens == {'entrada': 49, 'salida': 20, 'razonamiento': 12, 'total': 69}
    assert 'listo' not in repr(vars(guardia))


def test_cumple_el_protocolo_del_agente():
    import agente_rag
    guardia = S.GuardiaSalida()
    assert callable(guardia.revisar) and callable(guardia.registrar)
    assert agente_rag.FugaSalida is S.FugaSalida          # el agente captura la misma excepción que lanza la guardia
