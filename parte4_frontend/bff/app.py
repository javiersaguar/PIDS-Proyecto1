"""BFF del portal web (parte 4): la única puerta del navegador a la plataforma.

Guarda todas las claves (el navegador nunca ve ninguna), gestiona la sesión por cookie firmada, reenvía las
consultas a la API de acceso con la clave del cliente `frontend` y sirve la SPA construida desde `web/dist`.

Rutas públicas:   GET /api/salud · POST/GET/DELETE /api/sesion
Rutas protegidas: el resto de /api/* (consultas, catálogo, panel, tiempo real, auditoría, operaciones y chat),
                  incluidas con `prefix='/api'` y la dependencia `sesion_requerida` (401 «Sesión no iniciada»).
Lo demás:         la SPA (fallback a index.html) o, si no está construida, un JSON que explica cómo hacerlo.

    uv run uvicorn parte4_frontend.bff.app:app --port 8020 --reload

En los logs no se registran claves ni el contenido de las conversaciones.
"""
from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, FastAPI

from . import configuracion as C
from .estaticos import montar_estaticos
from .rutas import auditoria, catalogo, chat, consultas, gestos, observabilidad, operaciones, panel, salud, sesion, tiempo_real
from .seguridad import sesion_requerida

log = logging.getLogger('pids.frontend')

ROUTERS_PUBLICOS: tuple[APIRouter, ...] = (salud.router, sesion.router)
ROUTERS_PROTEGIDOS: tuple[APIRouter, ...] = (
    consultas.router, catalogo.router, panel.router, tiempo_real.router, auditoria.router, operaciones.router,
    chat.router, observabilidad.router, gestos.router,
)
TIEMPO_HTTP = httpx.Timeout(20.0, connect=5.0)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    cfg: C.Configuracion = app.state.configuracion
    for aviso in cfg.avisos():
        log.warning(aviso)
    app.state.http = httpx.AsyncClient(timeout=TIEMPO_HTTP)
    log.info('BFF del portal en marcha (%s); API de acceso en %s',
             'contenedor' if cfg.en_contenedor else 'host', cfg.acceso_url)
    try:
        yield
    finally:
        await app.state.http.aclose()


def crear_app(configuracion: C.Configuracion | None = None, dist: Path | None = None) -> FastAPI:
    """La aplicación. Los tests pasan su propia `Configuracion` (y un `dist` temporal para los estáticos)."""
    cfg = configuracion if configuracion is not None else C.configuracion()
    if not cfg.frontend_secreto:
        # Sin secreto configurado se firma con uno aleatorio por proceso: el portal funciona, pero las sesiones
        # no sobreviven a un reinicio (el aviso lo da el ciclo de vida).
        cfg = replace(cfg, frontend_secreto=secrets.token_urlsafe(32))
    if dist is not None:
        cfg = replace(cfg, dist_spa=dist)

    app = FastAPI(title='PIDS · Portal web (BFF)', version='0.1.0', lifespan=ciclo_de_vida,
                  docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)
    app.state.configuracion = cfg
    app.state.http = None

    for router in ROUTERS_PUBLICOS:
        app.include_router(router, prefix='/api')
    for router in ROUTERS_PROTEGIDOS:
        app.include_router(router, prefix='/api', dependencies=[Depends(sesion_requerida)])
    montar_estaticos(app, cfg.dist_spa)
    return app


app = crear_app()
