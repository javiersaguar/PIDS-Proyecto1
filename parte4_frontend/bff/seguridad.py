"""Sesión del portal (CONTRATOS.md §4): cookie `pids_sesion` firmada con HMAC-SHA256 y 12 horas de vida.

El valor de la cookie es `<caducidad_epoch>.<firma_hex>`; la firma cubre la caducidad con `FRONTEND_SECRETO`.
No hay estado en el servidor: cualquier réplica del BFF con el mismo secreto acepta la cookie. Las comparaciones
son en tiempo constante (`secrets.compare_digest`).

También viven aquí las dependencias de FastAPI que los routers de F1 y F2 pueden usar:

    from parte4_frontend.bff.seguridad import ConfiguracionDep, HttpDep

    @router.get('/catalogo')
    async def catalogo(cfg: ConfiguracionDep, http: HttpDep) -> dict: ...

La dependencia `sesion_requerida` la aplica `app.py` al incluir los routers protegidos; ningún router tiene que
declararla.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import Cookie, Depends, HTTPException, Request, Response

from .configuracion import DURACION_SESION, Configuracion

log = logging.getLogger('pids.frontend')

COOKIE = 'pids_sesion'


# --- lógica pura -------------------------------------------------------------------------------------------

def _firma(secreto: str, carga: str) -> str:
    return hmac.new(secreto.encode('utf-8'), carga.encode('utf-8'), hashlib.sha256).hexdigest()


def crear_valor_sesion(secreto: str, ahora: datetime | None = None, duracion: timedelta = DURACION_SESION) -> str:
    """`<caducidad>.<firma>` para una sesión que empieza en `ahora` y dura `duracion`."""
    ahora = ahora or datetime.now(timezone.utc)
    caducidad = str(int((ahora + duracion).timestamp()))
    return f'{caducidad}.{_firma(secreto, caducidad)}'


def sesion_valida(valor: str | None, secreto: str, ahora: datetime | None = None) -> bool:
    """La cookie es válida si la firma coincide (tiempo constante) y no ha caducado."""
    if not valor or not secreto or '.' not in valor:
        return False
    caducidad, firma = valor.rsplit('.', 1)
    if not caducidad.isdigit() or not secrets.compare_digest(firma, _firma(secreto, caducidad)):
        return False
    ahora = ahora or datetime.now(timezone.utc)
    return int(caducidad) > int(ahora.timestamp())


def clave_correcta(recibida: str, configurada: str) -> bool:
    """Comparación en tiempo constante; con la clave del portal vacía nadie entra."""
    if not configurada:
        return False
    return secrets.compare_digest(recibida.encode('utf-8'), configurada.encode('utf-8'))


# --- cookies -----------------------------------------------------------------------------------------------

def poner_cookie(respuesta: Response, valor: str, duracion: timedelta = DURACION_SESION, segura: bool = False) -> None:
    respuesta.set_cookie(COOKIE, valor, max_age=int(duracion.total_seconds()), httponly=True, samesite='lax',
                         secure=segura, path='/')


def borrar_cookie(respuesta: Response) -> None:
    respuesta.delete_cookie(COOKIE, path='/', httponly=True, samesite='lax')


# --- dependencias ------------------------------------------------------------------------------------------

def configuracion_actual(request: Request) -> Configuracion:
    """La configuración con la que se creó la aplicación (`crear_app(configuracion=...)`)."""
    return request.app.state.configuracion


def http_compartido(request: Request) -> httpx.AsyncClient:
    """El `httpx.AsyncClient` del ciclo de vida de la aplicación (uno por proceso)."""
    return request.app.state.http


ConfiguracionDep = Annotated[Configuracion, Depends(configuracion_actual)]
HttpDep = Annotated[httpx.AsyncClient, Depends(http_compartido)]


async def sesion_requerida(cfg: ConfiguracionDep,
                           pids_sesion: Annotated[str | None, Cookie(include_in_schema=False)] = None) -> None:
    """Todo `/api/*` salvo `/api/salud` y `/api/sesion` exige la cookie: sin ella, 401 «Sesión no iniciada»."""
    if not sesion_valida(pids_sesion, cfg.frontend_secreto):
        raise HTTPException(status_code=401, detail='Sesión no iniciada')
