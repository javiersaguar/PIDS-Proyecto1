"""Gestos de la parte 1 en el portal: los que reconoce el navegador entran en la plataforma, y los que entran por la
plataforma (la demo de Windows) llegan al portal.

  POST /api/gestos           {gesto, confianza, dispositivo} -> 202 {enviado}
  GET  /api/gestos/stream    text/event-stream: un evento `gesto` por cada gesto nuevo de la plataforma
  GET  /api/gestos/pregunta  ?anterior=… -> {pregunta}: la de ✌️, al azar (el mismo generador que los chatbots de Chainlit)

El navegador reconoce el gesto con la cámara y el MLP de la parte 1 (`web/src/gestos`); aquí solo llega la etiqueta
y la confianza, nunca la imagen ni los puntos de la mano. El BFF lo reenvía a `POST /gestos` de la API de captura
con la clave del cliente `gestos`, la misma que usa la demo de Windows, y así sigue el camino de siempre: la cola
`gestos` de Redpanda, los dos chatbots de Chainlit (si tienen un chat abierto) y los cuadros de Grafana.

El flujo retransmite `GET /gestos/stream` de la API de captura: cada conexión empieza en el final de la cola, así que
solo llegan gestos nuevos. El `dispositivo` va en cada evento para que la pestaña que lo hizo no lo repita.
Sin clave de gestos o con la captura caída, `enviado: false` y el flujo termina: el portal sigue funcionando y los
gestos siguen actuando en el propio navegador.
"""
from __future__ import annotations

import importlib.util
import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from types import ModuleType
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse, ServerSentEvent

from ..configuracion import RAIZ
from ..seguridad import ConfiguracionDep, HttpDep

log = logging.getLogger('pids.frontend')
router = APIRouter(tags=['gestos'])

MODELO = 'portal · mlp_muneca_escala_rot'
TIEMPO_ENVIO = 3.0
CAMPOS = ('gesto', 'confianza', 'dispositivo', 'instante')


@lru_cache(maxsize=1)
def modulo_gestos() -> ModuleType:
    """`parte3_chatbot/gestos.py`, cargado por su ruta (con un nombre propio, para no chocar con este módulo)."""
    especificacion = importlib.util.spec_from_file_location('pids_chatbot_gestos', RAIZ / 'parte3_chatbot' / 'gestos.py')
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class GestoPortal(BaseModel):
    gesto: Literal['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']
    confianza: float = Field(ge=0, le=1)
    dispositivo: str = Field(pattern=r'^portal-[a-z0-9]{6,32}$')


@router.post('/gestos', status_code=202)
async def enviar_gesto(gesto: GestoPortal, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    if not cfg.gestos_clave:
        return {'enviado': False}
    cuerpo = {**gesto.model_dump(), 'confianza': round(gesto.confianza, 3), 'modelo': MODELO}
    try:
        respuesta = await http.post(f'{cfg.captura_url.rstrip("/")}/gestos', json=cuerpo,
                                    headers={'X-API-Key': cfg.gestos_clave}, timeout=TIEMPO_ENVIO)
    except httpx.HTTPError as error:
        log.warning('no se ha podido enviar el gesto a la API de captura: %s', type(error).__name__)
        return {'enviado': False}
    return {'enviado': respuesta.status_code == 202}


@router.get('/gestos/pregunta')
async def pregunta(anterior: str | None = None) -> dict:
    return {'pregunta': modulo_gestos().pregunta_al_azar(anterior=anterior)}


async def _retransmitir(request: Request, http: httpx.AsyncClient, url: str, clave: str) -> AsyncIterator[ServerSentEvent]:
    from httpx_sse import aconnect_sse

    async with aconnect_sse(http, 'GET', url, headers={'X-API-Key': clave}, timeout=httpx.Timeout(10.0, read=None)) as fuente:
        async for evento in fuente.aiter_sse():
            if await request.is_disconnected():
                break
            if evento.event != 'gesto':
                continue
            try:
                datos = json.loads(evento.data)
            except ValueError:
                continue
            yield ServerSentEvent(event='gesto', data=json.dumps({k: datos.get(k) for k in CAMPOS}, ensure_ascii=False))


@router.get('/gestos/stream', response_class=EventSourceResponse,
            responses={200: {'description': 'Eventos `gesto` ({gesto, confianza, dispositivo, instante})',
                             'content': {'text/event-stream': {}}}})
async def flujo_gestos(request: Request, cfg: ConfiguracionDep, http: HttpDep) -> EventSourceResponse:
    if not cfg.gestos_clave:
        raise HTTPException(status_code=503, detail='El portal no tiene la clave de gestos de la API de captura')

    async def eventos() -> AsyncIterator[ServerSentEvent]:
        try:
            async for evento in _retransmitir(request, http, f'{cfg.captura_url.rstrip("/")}/gestos/stream', cfg.gestos_clave):
                yield evento
        except httpx.HTTPError as error:
            log.warning('flujo de gestos cortado: %s', type(error).__name__)

    return EventSourceResponse(eventos(), ping=15)
