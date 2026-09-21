"""Chatbot RAG de la plataforma (Chainlit + LangChain con Helmcode + Qdrant).

La lógica de cada mensaje está en agente_rag.py (filtro previo heredado, recuperación, herramientas y
barreras sobre las cifras) y el agente se construye en fabrica.py, igual que en las suites de evaluación.
Aquí solo va la interfaz:
  - cada llamada a una herramienta se muestra como un paso;
  - las fuentes recuperadas (documentos, zonas, ejemplos y fichas de agregados) van en un desplegable
    «Fuentes», con los tokens que ha costado el turno;
  - si la API rechaza la consulta, se muestra el motivo y un botón para lanzar la alternativa agregada.
Sin gestos: la integración con la parte 1 sigue en el chatbot de Ollama (parte3_chatbot/app.py).

Arranque: chainlit run app.py --host 0.0.0.0 --port 8000 --headless   (make chatbot-rag → http://localhost:8011)
"""
from __future__ import annotations

import sys
from pathlib import Path

import chainlit as cl

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / 'parte3_chatbot_rag'), str(RAIZ / 'parte3_chatbot')]

import fabrica  # noqa: E402
from agente import Turno  # noqa: E402
from herramientas import ClienteAcceso  # noqa: E402
from prompts import BIENVENIDA  # noqa: E402

TIPOS = {'doc': 'documentación', 'catalogo': 'catálogo', 'zona': 'zona', 'ejemplo': 'ejemplo', 'ficha': 'ficha de agregados'}


def fuentes_markdown(fuentes: list[dict], tokens: int | None = None) -> str:
    """Lista de fuentes sin repetir («**título** · tipo · fichero») y, si se conocen, los tokens del turno."""
    lineas, vistas = [], set()
    for fuente in fuentes:
        clave = (fuente.get('titulo'), fuente.get('fuente'))
        if clave in vistas:
            continue
        vistas.add(clave)
        partes = [f'**{fuente.get("titulo") or "sin título"}**', TIPOS.get(fuente.get('tipo'), fuente.get('tipo') or '')]
        if fuente.get('fuente'):
            partes.append(f'`{fuente["fuente"]}`')
        lineas.append('- ' + ' · '.join(p for p in partes if p))
    if not lineas:
        lineas.append('_Sin fuentes recuperadas: la respuesta sale solo de la API de acceso._')
    if tokens is not None:
        lineas.append(f'\n_Tokens del turno (entrada + salida): {tokens:,}_'.replace(',', '.'))
    return '\n'.join(lineas)


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


async def _mostrar(turno: Turno, tokens: int) -> None:
    fuentes = list(getattr(turno, 'fuentes', None) or [])
    if fuentes or tokens:
        nombre = f'Fuentes ({len(fuentes)})' if fuentes else 'Sin fuentes recuperadas'
        async with cl.Step(name=nombre, type='retrieval') as paso:
            paso.output = fuentes_markdown(fuentes, tokens)
    cl.user_session.set('alternativa', turno.alternativa)
    acciones = _acciones(turno.alternativa) if turno.alternativa else []
    await cl.Message(content=turno.respuesta, actions=acciones).send()


async def _responder(pregunta: str | None = None, alternativa: dict | None = None) -> None:
    agente, contador = cl.user_session.get('agente'), cl.user_session.get('contador')
    antes = contador.tokens
    if alternativa is not None:
        turno = await agente.responder_alternativa(alternativa, ejecutar=_con_paso)
    else:
        turno = await agente.responder(pregunta or '', ejecutar=_con_paso)
    await _mostrar(turno, contador.tokens - antes)


async def _ejecutar_alternativa() -> None:
    alternativa = cl.user_session.get('alternativa')
    if not alternativa:
        await cl.Message(content='No hay ninguna consulta pendiente.').send()
        return
    cl.user_session.set('alternativa', None)
    await _responder(alternativa=alternativa)


@cl.on_chat_start
async def inicio() -> None:
    acceso = fabrica.cliente_acceso('chatbot_rag')
    agente, contador = fabrica.agente_rag(acceso)
    cl.user_session.set('acceso', acceso)
    cl.user_session.set('agente', agente)
    cl.user_session.set('contador', contador)
    cl.user_session.set('alternativa', None)
    await cl.Message(content=BIENVENIDA).send()


@cl.on_message
async def mensaje(mensaje: cl.Message) -> None:
    await _responder(pregunta=mensaje.content)


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
    acceso = cl.user_session.get('acceso')
    if acceso:
        await acceso.cerrar()
