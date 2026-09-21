"""Catálogo y zonas (CONTRATOS.md §5), reenviados de la API de acceso con la clave del portal:

  GET /api/catalogo        -> Catalogo   (proxy de GET /catalogo: k mínimo, niveles, métricas, fuentes, barrios)
  GET /api/zonas?texto=    -> Zona[]     (proxy de GET /zonas: buscador de zonas por nombre)

Las dos respuestas cambian muy poco y cada petición a la API queda en la auditoría, así que se guardan en memoria
10 minutos (`servicios/acceso.py`). Si la API no responde: 503 con el motivo en español (sin ella no hay nada que
mostrar), nunca un 500.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: las rutas van sin `/api`.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import acceso as ACCESO

router = APIRouter(tags=['catálogo'])


def error_acceso(error: ACCESO.ServicioNoDisponible) -> HTTPException:
    """La API de acceso no responde o responde algo inesperado: 503 con el detalle (nunca la clave)."""
    return HTTPException(status_code=503, detail=f'La API de acceso no está disponible: {error.detalle}')


@router.get('/catalogo')
async def catalogo(cfg: ConfiguracionDep, http: HttpDep) -> dict:
    try:
        return await ACCESO.cliente(cfg, http).catalogo()
    except ACCESO.ServicioNoDisponible as error:
        raise error_acceso(error) from error


@router.get('/zonas')
async def zonas(cfg: ConfiguracionDep, http: HttpDep,
                texto: Annotated[str | None, Query(description='Parte del nombre de la zona (50 caracteres como '
                                                               'mucho, igual que la API)')] = None) -> list[dict]:
    try:
        return await ACCESO.cliente(cfg, http).zonas(texto)
    except ACCESO.ServicioNoDisponible as error:
        raise error_acceso(error) from error
