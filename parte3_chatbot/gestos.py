"""Integración con la parte 1: gestos recibidos en directo (SSE) desde la API de captura.

Desactivada por defecto (GESTOS_ACTIVOS=false): es la última fase del proyecto.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable

import httpx
from httpx_sse import aconnect_sse

log = logging.getLogger('pids.chatbot.gestos')

CAPTURA_URL = os.environ.get('CAPTURA_URL', 'http://captura:8000')
CAPTURA_CLAVE = os.environ.get('CAPTURA_CLAVE', '')
ACTIVOS = os.environ.get('GESTOS_ACTIVOS', 'false').lower() == 'true'
CONFIANZA_MINIMA = float(os.environ.get('GESTOS_CONFIANZA_MINIMA', '0.85'))

# Significado de cada gesto dentro del chatbot (distinto de los comandos del tanque)
ACCIONES = {
    'thumbsup': 'confirmar',
    'paper': 'cancelar',
    'ok': 'visto',
    'scissors': 'informe',
    'rock': 'volver',
}


async def escuchar(al_recibir: Callable[[str, dict], Awaitable[None]]) -> None:
    """Llama a `al_recibir(accion, evento)` por cada gesto con acción asociada. Reintenta si se corta."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as http:
                async with aconnect_sse(http, 'GET', f'{CAPTURA_URL}/gestos/stream',
                                        headers={'X-API-Key': CAPTURA_CLAVE}) as fuente:
                    async for sse in fuente.aiter_sse():
                        if sse.event != 'gesto':
                            continue
                        evento = json.loads(sse.data)
                        accion = ACCIONES.get(evento.get('gesto'))
                        if accion and evento.get('confianza', 0) >= CONFIANZA_MINIMA:
                            await al_recibir(accion, evento)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - la conexión se reintenta siempre
            log.warning('conexión de gestos perdida (%s); reintento en 5 s', e)
            await asyncio.sleep(5)
