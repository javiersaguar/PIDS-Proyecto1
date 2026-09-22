"""Integración con la parte 1: gestos recibidos en directo (SSE) desde la API de captura.

La usan los dos chatbots de Chainlit (el de Ollama y el RAG). Qué hace cada gesto está en `config/gestos.json`, la
misma tabla que lee TAXI AI en el portal: 👍 confirma la alternativa, ✋ la descarta y ✌️ hace la siguiente pregunta
de ejemplo. Leer en voz alta, abrir y cerrar solo existen en el portal: aquí esos gestos se ignoran.

Desactivada por defecto (GESTOS_ACTIVOS=false).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
from httpx_sse import aconnect_sse

log = logging.getLogger('pids.chatbot.gestos')

RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', Path(__file__).resolve().parents[1] / 'config'))
CONFIG = json.loads((RUTA_CONFIG / 'gestos.json').read_text(encoding='utf-8'))

CAPTURA_URL = os.environ.get('CAPTURA_URL', 'http://captura:8000')
CAPTURA_CLAVE = os.environ.get('CAPTURA_CLAVE', '')
ACTIVOS = os.environ.get('GESTOS_ACTIVOS', 'false').lower() == 'true'
CONFIANZA_MINIMA = float(os.environ.get('GESTOS_CONFIANZA_MINIMA', CONFIG['confianza_minima']))

# Significado de cada gesto dentro de los chatbots (distinto de los comandos del tanque de la demo de Windows)
ACCIONES: dict[str, str] = {gesto: datos['accion'] for gesto, datos in CONFIG['gestos'].items()}
PREGUNTAS: list[str] = CONFIG['preguntas']

Accion = Callable[[], Awaitable[None]]


def aviso(evento: dict) -> str:
    """El mensaje que deja el gesto en el chat: «👍 Gesto recibido: **thumbsup** → confirmar (97 %)»."""
    datos = CONFIG['gestos'].get(evento.get('gesto'), {})
    confianza = evento.get('confianza')
    porcentaje = f' ({confianza:.0%})' if isinstance(confianza, (int, float)) else ''
    return f'{datos.get("emoji", "✋")} Gesto recibido: **{evento.get("gesto")}** → {datos.get("accion", "?")}{porcentaje}'


def siguiente_pregunta(indice: int) -> tuple[str, int]:
    """La pregunta de ejemplo que toca y el índice de la siguiente (da la vuelta al llegar al final)."""
    return PREGUNTAS[indice % len(PREGUNTAS)], (indice + 1) % len(PREGUNTAS)


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


def enganchar_a_chainlit(acciones: dict[str, Accion]) -> asyncio.Task | None:
    """Con GESTOS_ACTIVOS, escucha los gestos para el chat de Chainlit que se está abriendo y ejecuta
    `acciones[accion]` por cada uno. Devuelve la tarea (para cancelarla al cerrar el chat) o None si están
    desactivados. Los gestos cuya acción no está en `acciones` (los del portal) no dejan rastro en el chat."""
    if not ACTIVOS:
        return None
    import chainlit as cl
    from chainlit.context import context_var

    ctx = context_var.get()

    async def al_recibir(accion: str, evento: dict) -> None:
        hacer = acciones.get(accion)
        if hacer is None:
            return
        # El SSE llega en otra tarea; la sesión de Chainlit es la de este chat.
        token = context_var.set(ctx)
        try:
            await cl.Message(content=aviso(evento)).send()
            await hacer()
        finally:
            context_var.reset(token)

    return asyncio.create_task(escuchar(al_recibir))
