"""Gestos de la parte 1 en los chatbots: la tabla común (`config/gestos.json`) y el módulo que la usa en los dos
chatbots de Chainlit (`parte3_chatbot/gestos.py`). TAXI AI, en el portal, lee la misma tabla (sus tests están en
`parte4_frontend/web/src/gestos`)."""
import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'parte3_chatbot'))

import gestos as G  # noqa: E402

from parte4_frontend.demo import instantanea as INSTANTANEA  # noqa: E402

CLASES_PARTE1 = json.loads((RAIZ / 'parte1_gestos' / 'modelos' / 'plan_20260917-0042_mlp_muneca_escala_rot'
                            / 'etiquetas.json').read_text(encoding='utf-8'))['clases']


def test_la_tabla_cubre_los_seis_gestos_del_modelo_con_acciones_distintas():
    assert sorted(G.CONFIG['gestos']) == sorted(CLASES_PARTE1)
    acciones = list(G.ACCIONES.values())
    assert len(set(acciones)) == len(acciones)
    assert set(acciones) == {'confirmar', 'cancelar', 'siguiente', 'leer', 'abrir', 'cerrar'}
    assert G.ACCIONES['thumbsup'] == 'confirmar' and G.ACCIONES['paper'] == 'cancelar'   # como en el vídeo de CU8
    assert 0.5 <= G.CONFIANZA_MINIMA <= 1


def test_las_preguntas_de_la_v_estan_grabadas_en_la_demostracion_publica():
    # ✌️ tiene que funcionar también en Vercel sin el equipo: cada pregunta tiene su conversación grabada
    assert set(G.PREGUNTAS) <= set(INSTANTANEA.PREGUNTAS_CHAT)
    assert 'Dame el viaje' in G.PREGUNTAS[-1]                  # la última se rechaza y 👍 confirma su alternativa


def test_siguiente_pregunta_da_la_vuelta():
    n = len(G.PREGUNTAS)
    assert G.siguiente_pregunta(0) == (G.PREGUNTAS[0], 1)
    assert G.siguiente_pregunta(n - 1) == (G.PREGUNTAS[-1], 0)
    assert G.siguiente_pregunta(n + 1)[0] == G.PREGUNTAS[1]


def test_aviso_dice_el_gesto_la_accion_y_la_confianza():
    assert G.aviso({'gesto': 'thumbsup', 'confianza': 0.97}) == '👍 Gesto recibido: **thumbsup** → confirmar (97%)'
    assert G.aviso({'gesto': 'scissors'}) == '✌️ Gesto recibido: **scissors** → siguiente'


def test_escuchar_entrega_solo_gestos_con_accion_y_confianza_suficiente(monkeypatch):
    flujo = ''.join(f'event: gesto\ndata: {json.dumps(e)}\n\n' for e in [
        {'gesto': 'thumbsup', 'confianza': 0.97},
        {'gesto': 'paper', 'confianza': 0.5},              # poca confianza
        {'gesto': 'None', 'confianza': 0.99},              # sin gesto
        {'gesto': 'scissors', 'confianza': 0.9},
    ]) + 'event: otro\ndata: {}\n\n'
    conexiones = []

    def captura(peticion: httpx.Request) -> httpx.Response:
        conexiones.append(peticion.headers.get('x-api-key'))
        if len(conexiones) > 1:                          # al terminar el flujo reconecta: aquí se corta la prueba
            raise asyncio.CancelledError
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=flujo.encode())

    original = httpx.AsyncClient
    monkeypatch.setattr(G.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(captura), **kw))
    monkeypatch.setattr(G, 'CAPTURA_CLAVE', 'clave-chatbot')
    recibidos = []

    async def al_recibir(accion, evento):
        recibidos.append((accion, evento['gesto']))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(G.escuchar(al_recibir))
    assert recibidos == [('confirmar', 'thumbsup'), ('siguiente', 'scissors')]
    assert conexiones[0] == 'clave-chatbot'


def test_sin_gestos_activos_no_se_engancha_nada(monkeypatch):
    monkeypatch.setattr(G, 'ACTIVOS', False)
    assert G.enganchar_a_chainlit({'confirmar': None}) is None
