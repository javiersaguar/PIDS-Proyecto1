"""Chatbot de la plataforma (Chainlit + LLM local con Ollama).

Flujo de cada mensaje:
  1. Filtro previo: si parece una petición de datos individuales, se rechaza sin pasar por el LLM.
  2. El LLM decide qué herramienta usar; las herramientas llaman a la API de acceso (nunca a la base).
  3. Si la API rechaza, se muestra el motivo y un botón para lanzar la alternativa agregada.
     Con la integración de gestos activa, 👍 confirma y ✋ cancela.

Arranque: chainlit run app.py --host 0.0.0.0 --port 8000 --headless
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import chainlit as cl
from ollama import AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gestos  # noqa: E402
from herramientas import ESQUEMAS, ClienteAcceso, parece_individual  # noqa: E402
from prompts import BIENVENIDA, SISTEMA  # noqa: E402

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://ollama:11434')
MODELO = os.environ.get('OLLAMA_MODELO', 'llama3.1:8b')
MAX_PASOS = 5


def _acciones(alternativa: dict) -> list[cl.Action]:
    return [
        cl.Action(name='aceptar_alternativa', payload={'consulta': alternativa}, label='✅ Consultar la alternativa'),
        cl.Action(name='cancelar', payload={}, label='✖ Cancelar'),
    ]


async def _mostrar_rechazo(resultado: dict) -> None:
    motivos = '\n'.join(f'- {m}' for m in resultado.get('motivos', []))
    alternativa = resultado.get('alternativa')
    texto = f'🔒 **Consulta rechazada por privacidad**\n{motivos}'
    if alternativa:
        cl.user_session.set('alternativa', alternativa)
        texto += f'\n\nPuedo responder esta alternativa agregada:\n```json\n{json.dumps(alternativa, indent=2)}\n```'
        await cl.Message(content=texto, actions=_acciones(alternativa)).send()
    else:
        await cl.Message(content=texto + '\n\nPrueba con volúmenes por hora y zona, o por día y barrio.').send()


async def _conversar(texto: str) -> None:
    acceso: ClienteAcceso = cl.user_session.get('acceso')
    llm: AsyncClient = cl.user_session.get('llm')
    mensajes: list = cl.user_session.get('mensajes')
    mensajes.append({'role': 'user', 'content': texto})

    for _ in range(MAX_PASOS):
        respuesta = await llm.chat(model=MODELO, messages=mensajes, tools=ESQUEMAS)
        mensajes.append(respuesta.message)
        llamadas = respuesta.message.tool_calls or []
        if not llamadas:
            await cl.Message(content=respuesta.message.content or '(sin respuesta)').send()
            return
        for llamada in llamadas:
            nombre, argumentos = llamada.function.name, dict(llamada.function.arguments or {})
            async with cl.Step(name=nombre, type='tool') as paso:
                paso.input = argumentos
                resultado = await acceso.ejecutar(nombre, argumentos)
                paso.output = resultado
            if isinstance(resultado, dict) and resultado.get('resultado') == 'rechazada' and resultado.get('alternativa'):
                cl.user_session.set('alternativa', resultado['alternativa'])
            mensajes.append({'role': 'tool', 'tool_name': nombre,
                             'content': json.dumps(resultado, ensure_ascii=False, default=str)[:12000]})
    await cl.Message(content='No he podido completar la consulta en pocos pasos; ¿puedes concretarla?').send()


async def _ejecutar_alternativa() -> None:
    alternativa = cl.user_session.get('alternativa')
    if not alternativa:
        await cl.Message(content='No hay ninguna consulta pendiente.').send()
        return
    cl.user_session.set('alternativa', None)
    await _conversar('Ejecuta exactamente esta consulta agregada y resume el resultado: '
                     + json.dumps(alternativa, ensure_ascii=False))


@cl.on_chat_start
async def inicio() -> None:
    cl.user_session.set('acceso', ClienteAcceso())
    cl.user_session.set('llm', AsyncClient(host=OLLAMA_URL))
    cl.user_session.set('mensajes', [{'role': 'system', 'content': SISTEMA}])
    cl.user_session.set('alternativa', None)
    if gestos.ACTIVOS:
        async def al_recibir(accion: str, evento: dict) -> None:
            await cl.Message(content=f'✋ Gesto recibido: **{evento["gesto"]}** → {accion}').send()
            if accion == 'confirmar':
                await _ejecutar_alternativa()
            elif accion == 'cancelar':
                cl.user_session.set('alternativa', None)
        cl.user_session.set('tarea_gestos', asyncio.create_task(gestos.escuchar(al_recibir)))
    await cl.Message(content=BIENVENIDA).send()


@cl.on_message
async def mensaje(mensaje: cl.Message) -> None:
    if parece_individual(mensaje.content):
        acceso: ClienteAcceso = cl.user_session.get('acceso')
        await _mostrar_rechazo(await acceso.solicitud_individual(mensaje.content))
        return
    await _conversar(mensaje.content)


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
