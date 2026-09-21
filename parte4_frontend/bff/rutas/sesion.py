"""Sesión del portal (CONTRATOS.md §4):

  POST   /api/sesion  {"clave": "…"}  -> 204 y cookie `pids_sesion`; 401 si la clave no coincide
  GET    /api/sesion                  -> {"autenticado": true|false}
  DELETE /api/sesion                  -> 204 y borra la cookie

Nunca se registra la clave recibida: solo si el intento fue correcto o no y desde qué dirección.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..seguridad import (ConfiguracionDep, borrar_cookie, clave_correcta, crear_valor_sesion, poner_cookie,
                         sesion_valida)

log = logging.getLogger('pids.frontend')
router = APIRouter(tags=['sesión'])

RETARDO_FALLO = 0.3      # segundos: frena la fuerza bruta sin molestar a una persona


class Credenciales(BaseModel):
    clave: str = Field(min_length=1, max_length=256)


def _quien(request: Request) -> str:
    return request.client.host if request.client else 'desconocido'


@router.post('/sesion', status_code=204, response_class=Response)
async def iniciar_sesion(credenciales: Credenciales, request: Request, cfg: ConfiguracionDep) -> Response:
    if not clave_correcta(credenciales.clave, cfg.frontend_clave):
        log.warning('Intento de inicio de sesión fallido desde %s', _quien(request))
        await asyncio.sleep(RETARDO_FALLO)
        raise HTTPException(status_code=401, detail='Clave incorrecta')
    log.info('Sesión iniciada desde %s', _quien(request))
    respuesta = Response(status_code=204)
    poner_cookie(respuesta, crear_valor_sesion(cfg.frontend_secreto, duracion=cfg.duracion_sesion),
                 duracion=cfg.duracion_sesion, segura=request.url.scheme == 'https')
    return respuesta


@router.get('/sesion')
async def estado_sesion(cfg: ConfiguracionDep,
                        pids_sesion: Annotated[str | None, Cookie(include_in_schema=False)] = None) -> dict:
    return {'autenticado': sesion_valida(pids_sesion, cfg.frontend_secreto)}


@router.delete('/sesion', status_code=204, response_class=Response)
async def cerrar_sesion() -> Response:
    respuesta = Response(status_code=204)
    borrar_cookie(respuesta)
    return respuesta
