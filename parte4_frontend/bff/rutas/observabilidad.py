"""Observabilidad (sección del portal): los cuadros de Grafana con sus datos, para que la SPA los dibuje.

  GET /api/observabilidad/cuadros           -> [{uid, titulo, periodo}]
  GET /api/observabilidad/cuadros/{uid}     -> {uid, titulo, periodo, actualizado, disponible, paneles: [...]}; 404 si no existe

Solo se ejecutan las consultas de los ficheros de los cuadros (`servicios/observabilidad.py`): la petición lleva un
uid, nunca una consulta de Prometheus. `app.py` incluye este router con `prefix='/api'` y la dependencia de sesión.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import observabilidad as OBS

router = APIRouter(tags=['observabilidad'])


@router.get('/observabilidad/cuadros')
async def cuadros() -> list[dict]:
    return OBS.lista()


@router.get('/observabilidad/cuadros/{uid}')
async def cuadro(uid: str, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    datos = await OBS.cuadro_con_datos(uid, http, cfg.prometheus_url, cfg.grafana_url)
    if datos is None:
        raise HTTPException(status_code=404, detail='No hay ningún cuadro con ese nombre')
    return datos
