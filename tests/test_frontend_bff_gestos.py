"""BFF del portal (parte 4), gestos: el navegador reconoce el gesto y el BFF lo lleva a la API de captura con la clave
del cliente `gestos`; los gestos de la plataforma (la demo de Windows) vuelven al portal por SSE. Sin red: la API de
captura es un `httpx.MockTransport`."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from parte4_frontend.bff import app as A
from parte4_frontend.bff import configuracion as C
from parte4_frontend.bff import seguridad as S

ENTORNO = {'PUERTO_CAPTURA': '8001', 'CAPTURA_CLAVE_GESTOS': 'clave-gestos', 'CAPTURA_CLAVE_SIMULADOR': 'clave-sim',
           'FRONTEND_CLAVE': 'portal', 'FRONTEND_SECRETO': 'secreto'}
GESTO = {'gesto': 'thumbsup', 'confianza': 0.9731, 'dispositivo': 'portal-a1b2c3d4'}
ASYNC_CLIENT = httpx.AsyncClient
FLUJO = (': ping\n\n'
         'event: gesto\ndata: {"gesto": "paper", "confianza": 0.98, "modelo": "mlp", "dispositivo": "PORTATIL", '
         '"instante": "2026-09-22T18:00:00+00:00", "cliente": "gestos"}\n\n'
         'event: otro\ndata: {}\n\n'
         'event: gesto\ndata: no es json\n\n')


class Captura:
    def __init__(self):
        self.recibidos: list[tuple[str | None, dict]] = []
        self.caida = False

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if self.caida:
            raise httpx.ConnectError('caída', request=peticion)
        if peticion.method == 'POST' and peticion.url.path == '/gestos':
            self.recibidos.append((peticion.headers.get('x-api-key'), json.loads(peticion.content)))
            return httpx.Response(202, json={'aceptado': True})
        if peticion.url.path == '/gestos/stream':
            return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=FLUJO.encode())
        return httpx.Response(404)


@pytest.fixture
def captura() -> Captura:
    return Captura()


def _cliente(entorno, captura, tmp_path, monkeypatch):
    cfg = C.Configuracion.desde_entorno(entorno, contenedor=False)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: ASYNC_CLIENT(transport=httpx.MockTransport(captura), **kw))
    c = TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist'))
    c.cookies.set('pids_sesion', S.crear_valor_sesion(cfg.frontend_secreto))
    return c


@pytest.fixture
def cliente(captura, tmp_path, monkeypatch):
    with _cliente(ENTORNO, captura, tmp_path, monkeypatch) as c:
        yield c


def test_sin_sesion_da_401(tmp_path):
    cfg = C.Configuracion.desde_entorno(ENTORNO, contenedor=False)
    with TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist')) as c:
        assert c.post('/api/gestos', json=GESTO).status_code == 401
        assert c.get('/api/gestos/stream').status_code == 401


def test_el_gesto_del_navegador_entra_por_la_api_de_captura_como_cliente_gestos(cliente, captura):
    respuesta = cliente.post('/api/gestos', json=GESTO)
    assert respuesta.status_code == 202 and respuesta.json() == {'enviado': True}
    clave, cuerpo = captura.recibidos[0]
    assert clave == 'clave-gestos'                                   # nunca la del simulador
    assert cuerpo == {'gesto': 'thumbsup', 'confianza': 0.973, 'dispositivo': 'portal-a1b2c3d4',
                      'modelo': 'portal · mlp_muneca_escala_rot'}   # solo etiqueta y confianza: ni imagen ni puntos


@pytest.mark.parametrize('cambio', [{'gesto': 'None'}, {'gesto': 'thumbsdown'}, {'confianza': 1.5},
                                    {'dispositivo': 'PORTATIL-DE-ALGUIEN'}, {'dispositivo': 'portal-x'}])
def test_valida_el_gesto_antes_de_enviarlo(cliente, captura, cambio):
    assert cliente.post('/api/gestos', json={**GESTO, **cambio}).status_code == 422
    assert captura.recibidos == []


def test_sin_clave_o_con_la_captura_caida_no_se_envia_y_no_falla(captura, tmp_path, monkeypatch):
    sin_clave = {k: v for k, v in ENTORNO.items() if k != 'CAPTURA_CLAVE_GESTOS'}
    with _cliente(sin_clave, captura, tmp_path, monkeypatch) as c:
        assert c.post('/api/gestos', json=GESTO).json() == {'enviado': False}
        assert c.get('/api/gestos/stream').status_code == 503
    assert captura.recibidos == []
    captura.caida = True
    with _cliente(ENTORNO, captura, tmp_path, monkeypatch) as c:
        assert c.post('/api/gestos', json=GESTO).json() == {'enviado': False}


def test_el_flujo_retransmite_solo_los_gestos_y_sin_el_cliente(cliente):
    with cliente.stream('GET', '/api/gestos/stream') as respuesta:
        assert respuesta.status_code == 200
        texto = respuesta.read().decode()
    datos = [json.loads(linea.removeprefix('data: ')) for linea in texto.splitlines() if linea.startswith('data: ')]
    assert datos == [{'gesto': 'paper', 'confianza': 0.98, 'dispositivo': 'PORTATIL',
                      'instante': '2026-09-22T18:00:00+00:00'}]
    assert texto.count('event: gesto') == 1


def test_la_pregunta_de_la_v_sale_del_generador_de_los_chatbots(cliente):
    primera = cliente.get('/api/gestos/pregunta').json()['pregunta']
    assert primera and '{' not in primera
    otra = cliente.get('/api/gestos/pregunta', params={'anterior': primera}).json()['pregunta']
    assert otra != primera
