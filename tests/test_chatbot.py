"""Filtro previo del chatbot y herramientas (sin LLM ni API reales)."""
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'parte3_chatbot'))

import herramientas as H  # noqa: E402


@pytest.mark.parametrize('texto', [
    '¿Qué matrícula tenía el taxi que salió de JFK?',
    'Dame el viaje de las 3:12 desde Times Square',
    '¿Quién cogió un taxi en Harlem anoche?',
    'Quiero el teléfono del pasajero',
    'Enséñame los viajes de un pasajero concreto',
    'Busca por el identificador del viaje 1234',
])
def test_detecta_peticiones_individuales(texto):
    assert H.parece_individual(texto)


@pytest.mark.parametrize('texto', [
    '¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?',
    '¿Qué barrio tuvo más viajes el 3 de marzo?',
    'Propina media en Manhattan la primera semana de febrero',
])
def test_no_bloquea_consultas_agregadas(texto):
    assert not H.parece_individual(texto)


def test_esquemas_de_herramientas_coinciden_con_el_cliente():
    for esquema in H.ESQUEMAS:
        assert hasattr(H.ClienteAcceso, esquema['function']['name'])


async def test_cliente_devuelve_el_rechazo_y_limpia_argumentos():
    recibido = {}

    def responder(peticion: httpx.Request) -> httpx.Response:
        recibido['json'] = peticion.content.decode()
        recibido['clave'] = peticion.headers['X-API-Key']
        return httpx.Response(403, json={'resultado': 'rechazada', 'motivos': ['x'], 'alternativa': None})

    cliente = H.ClienteAcceso(url='http://acceso', clave='k')
    cliente.http = httpx.AsyncClient(base_url='http://acceso', headers={'X-API-Key': 'k'},
                                     transport=httpx.MockTransport(responder))
    r = await cliente.ejecutar('consultar_viajes', {'nivel': 'hora_zona', 'desde': 'a', 'hasta': 'b',
                                                    'zona_origen': None, 'metricas': []})
    assert r['resultado'] == 'rechazada'
    assert 'zona_origen' not in recibido['json'] and 'metricas' not in recibido['json']
    assert recibido['clave'] == 'k'
    assert (await cliente.ejecutar('borrar_todo', {}))['error'].startswith('herramienta desconocida')
    await cliente.cerrar()
