"""Asistente conversacional (CONTRATOS.md §5, «chat (F2)»):

  GET    /api/chat/motores                          -> Motor[] (`rag` con `disponible: false` si su módulo no está)
  POST   /api/chat/sesiones {motor}                 -> 201 {id, motor}; 422 motor desconocido; 409 no disponible
  DELETE /api/chat/sesiones/{id}                    -> 204; 404 si no existe o ha caducado
  POST   /api/chat/sesiones/{id}/mensajes {texto}   -> text/event-stream: `paso`*, luego `respuesta` o `error`
  POST   /api/chat/sesiones/{id}/alternativa        -> el mismo flujo con la alternativa pendiente; 400 si no hay
  409 si la sesión ya tiene un mensaje en curso.

La lógica vive en `servicios/chat.py`; aquí solo se validan los cuerpos, se traducen sus errores a códigos HTTP
y sus eventos a SSE (campo `event` con el tipo y `data` con el JSON, `ensure_ascii=False`). La sesión se reserva
antes de empezar a emitir, para que el 409 y el 400 lleguen como códigos HTTP y no dentro de un 200.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: las rutas van sin `/api` y no
comprueban la cookie. En los logs no se registra el contenido de los mensajes (ni la pregunta ni la respuesta).
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sse_starlette import EventSourceResponse, ServerSentEvent

from ..servicios.chat import ErrorChat, Evento, Sesiones

log = logging.getLogger('pids.frontend')
router = APIRouter(tags=['chat'])

RESPUESTA_SSE = {200: {'description': 'Eventos `paso` (EventoPaso), `respuesta` (EventoRespuesta) y `error` ({detail})',
                       'content': {'text/event-stream': {}}}}


class NuevaSesion(BaseModel):
    motor: Literal['ollama', 'rag']


class Mensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)

    @field_validator('texto')
    @classmethod
    def _con_contenido(cls, texto: str) -> str:
        if not texto.strip():
            raise ValueError('el texto no puede estar en blanco')
        return texto.strip()


# --- dependencias y traducción de errores --------------------------------------------------------------------

def sesiones_de(request: Request) -> Sesiones:
    """Las sesiones de chat de esta aplicación: un `Sesiones` por proceso, creado al primer uso con la
    configuración con la que se construyó la app (los tests la pasan a `crear_app`)."""
    estado = request.app.state
    if getattr(estado, 'chat_sesiones', None) is None:
        estado.chat_sesiones = Sesiones(estado.configuracion)
    return estado.chat_sesiones


SesionesDep = Annotated[Sesiones, Depends(sesiones_de)]


@contextmanager
def _como_http() -> Iterator[None]:
    """`ErrorChat` del servicio -> `HTTPException` con su código y su `detail`."""
    try:
        yield
    except ErrorChat as e:
        raise HTTPException(status_code=e.codigo, detail=e.detail) from None


async def _sse(eventos: AsyncIterator[Evento]) -> AsyncIterator[ServerSentEvent]:
    async for evento in eventos:
        yield ServerSentEvent(event=evento.tipo, data=json.dumps(evento.datos, ensure_ascii=False, default=str))


# --- rutas ---------------------------------------------------------------------------------------------------

@router.get('/chat/motores')
async def listar_motores(sesiones: SesionesDep) -> list[dict]:
    return [asdict(motor) for motor in sesiones.motores()]


@router.post('/chat/sesiones', status_code=201)
async def crear_sesion(nueva: NuevaSesion, sesiones: SesionesDep) -> dict:
    with _como_http():
        sesion = await sesiones.crear(nueva.motor)
    return {'id': sesion.id, 'motor': sesion.motor}


@router.delete('/chat/sesiones/{id_sesion}', status_code=204, response_class=Response)
async def cerrar_sesion(id_sesion: str, sesiones: SesionesDep) -> Response:
    with _como_http():
        await sesiones.cerrar(id_sesion)
    return Response(status_code=204)


@router.post('/chat/sesiones/{id_sesion}/mensajes', response_class=EventSourceResponse, responses=RESPUESTA_SSE)
async def enviar_mensaje(id_sesion: str, mensaje: Mensaje, sesiones: SesionesDep) -> EventSourceResponse:
    with _como_http():
        sesion = await sesiones.obtener(id_sesion)
        await sesiones.reservar(sesion)
    log.info('Sesión de chat %s: mensaje recibido (%d caracteres)', sesion.id, len(mensaje.texto))
    return EventSourceResponse(_sse(sesiones.responder(sesion, mensaje.texto)))


@router.post('/chat/sesiones/{id_sesion}/alternativa', response_class=EventSourceResponse, responses=RESPUESTA_SSE)
async def consultar_alternativa(id_sesion: str, sesiones: SesionesDep) -> EventSourceResponse:
    with _como_http():
        sesion = await sesiones.obtener(id_sesion)
        await sesiones.reservar(sesion, alternativa=True)
    log.info('Sesión de chat %s: se consulta la alternativa pendiente', sesion.id)
    return EventSourceResponse(_sse(sesiones.responder_alternativa(sesion)))
