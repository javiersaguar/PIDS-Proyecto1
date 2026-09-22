"""Chatbot de la plataforma (Chainlit + LLM local con Ollama).

La lógica de cada mensaje está en agente.py (filtro previo, herramientas y barreras sobre las cifras),
la misma que usan las pruebas. Aquí solo va la interfaz:
  - cada llamada a una herramienta se muestra como un paso;
  - si la API rechaza la consulta, se muestra el motivo y un botón para lanzar la alternativa agregada.
    Con la integración de gestos activa, 👍 confirma, ✋ cancela y ✌️ hace la siguiente pregunta de ejemplo
    (`gestos.py`, con la tabla de `config/gestos.json`).

Arranque: chainlit run app.py --host 0.0.0.0 --port 8000 --headless
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

import chainlit as cl
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


async def _cancelar_alternativa() -> None:
    cl.user_session.set('alternativa', None)
    await cl.Message(content='De acuerdo, consulta cancelada.').send()


async def _pregunta_de_ejemplo() -> None:
    """✌️: la siguiente pregunta de `config/gestos.json`, como si la hubiera escrito el usuario."""
    pregunta, siguiente = gestos.siguiente_pregunta(cl.user_session.get('pregunta_gesto') or 0)
    cl.user_session.set('pregunta_gesto', siguiente)
    await cl.Message(content=pregunta, author='Tú', type='user_message').send()
    agente: Agente = cl.user_session.get('agente')
    await _mostrar(await agente.responder(pregunta, ejecutar=_con_paso))


@cl.on_chat_start
async def inicio() -> None:
    acceso = ClienteAcceso()
    cl.user_session.set('acceso', acceso)
    cl.user_session.set('agente', Agente(acceso, AsyncClient(host=OLLAMA_URL)))
    cl.user_session.set('alternativa', None)
    cl.user_session.set('tarea_gestos', gestos.enganchar_a_chainlit({
        'confirmar': _ejecutar_alternativa,
        'cancelar': _cancelar_alternativa,
        'siguiente': _pregunta_de_ejemplo,
    }))
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
    await _cancelar_alternativa()


@cl.on_chat_end
async def fin() -> None:
    tarea = cl.user_session.get('tarea_gestos')
    if tarea:
        tarea.cancel()
    acceso = cl.user_session.get('acceso')
    if acceso:
        await acceso.cerrar()
