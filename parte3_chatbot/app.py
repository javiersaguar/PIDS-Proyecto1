"""Chatbot de la plataforma (Chainlit + LLM local con Ollama).

La lógica de cada mensaje está en agente.py (filtro previo, herramientas y barreras sobre las cifras),
la misma que usan las pruebas. Aquí solo va la interfaz:
  - cada llamada a una herramienta se muestra como un paso;
  - si la API rechaza la consulta, se muestra el motivo y un botón para lanzar la alternativa agregada.
    Con la integración de gestos activa, 👍 confirma y ✋ cancela.

Arranque: chainlit run app.py --host 0.0.0.0 --port 8000 --headless
"""
from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path

import chainlit as cl
from chainlit.context import context_var
from ollama import AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gestos  # noqa: E402
from agente import Agente, Turno  # noqa: E402
from herramientas import ClienteAcceso  # noqa: E402
from prompts import BIENVENIDA  # noqa: E402

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://ollama:11434')


@cl.password_auth_callback
def autenticar(usuario: str, clave: str) -> cl.User | None:
    """Una sola cuenta de equipo. Sin CHATBOT_CLAVE no entra nadie."""
    esperada = os.environ.get('CHATBOT_CLAVE', '')
    if esperada and usuario == os.environ.get('CHATBOT_USUARIO', 'equipo') and secrets.compare_digest(clave, esperada):
        return cl.User(identifier=usuario)
    return None


def _acciones(alternativa: dict) -> list[cl.Action]:
    return [
        cl.Action(name='aceptar_alternativa', payload={'consulta': alternativa}, label='✅ Consultar la alternativa'),
        cl.Action(name='cancelar', payload={}, label='✖ Cancelar'),
    ]


async def _con_paso(nombre: str, argumentos: dict):
    """Ejecuta la herramienta mostrándola en la interfaz como un paso."""
    acceso: ClienteAcceso = cl.user_session.get('acceso')
    async with cl.Step(name=nombre, type='tool') as paso:
        paso.input = argumentos
        resultado = await acceso.ejecutar(nombre, argumentos)
        paso.output = resultado
    return resultado


async def _mostrar(turno: Turno) -> None:
    cl.user_session.set('alternativa', turno.alternativa)
    acciones = _acciones(turno.alternativa) if turno.alternativa else []
    await cl.Message(content=turno.respuesta, actions=acciones).send()


async def _ejecutar_alternativa() -> None:
    alternativa = cl.user_session.get('alternativa')
    if not alternativa:
        await cl.Message(content='No hay ninguna consulta pendiente.').send()
        return
    cl.user_session.set('alternativa', None)
    agente: Agente = cl.user_session.get('agente')
    await _mostrar(await agente.responder_alternativa(alternativa, ejecutar=_con_paso))


@cl.on_chat_start
async def inicio() -> None:
    acceso = ClienteAcceso()
    cl.user_session.set('acceso', acceso)
    cl.user_session.set('agente', Agente(acceso, AsyncClient(host=OLLAMA_URL)))
    cl.user_session.set('alternativa', None)
    if gestos.ACTIVOS:
        ctx = context_var.get()

        async def al_recibir(accion: str, evento: dict) -> None:
            # El SSE llega en otra tarea; la sesión de Chainlit es la de este chat.
            token = context_var.set(ctx)
            try:
                await cl.Message(content=f'✋ Gesto recibido: **{evento["gesto"]}** → {accion}').send()
                if accion == 'confirmar':
                    await _ejecutar_alternativa()
                elif accion == 'cancelar':
                    cl.user_session.set('alternativa', None)
                    await cl.Message(content='De acuerdo, consulta cancelada.').send()
            finally:
                context_var.reset(token)
        cl.user_session.set('tarea_gestos', asyncio.create_task(gestos.escuchar(al_recibir)))
    await cl.Message(content=BIENVENIDA).send()


@cl.on_message
async def mensaje(mensaje: cl.Message) -> None:
    agente: Agente = cl.user_session.get('agente')
    await _mostrar(await agente.responder(mensaje.content, ejecutar=_con_paso))


@cl.action_callback('aceptar_alternativa')
async def aceptar(accion: cl.Action) -> None:
    cl.user_session.set('alternativa', accion.payload.get('consulta'))
    await _ejecutar_alternativa()


@cl.action_callback('cancelar')
async def cancelar(_: cl.Action) -> None:
    cl.user_session.set('alternativa', None)
    await cl.Message(content='De acuerdo, consulta cancelada.').send()


@cl.on_chat_end
async def fin() -> None:
    tarea = cl.user_session.get('tarea_gestos')
    if tarea:
        tarea.cancel()
    acceso = cl.user_session.get('acceso')
    if acceso:
        await acceso.cerrar()
