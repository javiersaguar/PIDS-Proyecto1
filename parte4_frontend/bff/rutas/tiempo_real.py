"""`GET /api/tiempo-real?horas=6` -> `TiempoReal` (CONTRATOS.md §5): lo que Spark ha publicado del flujo en directo.

Todo sale de consultas normales a la API de acceso con `fuente=tiempo_real` (colecciones `tr_*`):
- `ultimo_dia`: el último día con datos (`dia_barrio`, diciembre de 2020 y hacia atrás, mes a mes).
- `por_hora`: las últimas N horas con datos (`hora_zona`), sumando solo los grupos visibles y contando los
  enmascarados. Un día entero con todas las zonas supera las 500 filas que la API devuelve como máximo, así que
  en ese caso se pide hora a hora desde el final (`servicios/acceso.py`).
- `por_zona_ultima_hora`: las filas de la última hora tal cual las da la API (con sus `"<10"`).
- `frescura`: de Prometheus (`publico_ultima_actualizacion_timestamp_segundos`).

La página se refresca cada 30 s y cada consulta queda en la auditoría: el resultado se guarda en memoria unos
segundos. API caída -> `acceso_disponible: false` (campo añadido al contrato), listas vacías y 200.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: la ruta va sin `/api`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Query

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import acceso as ACCESO
from ..servicios import prometheus as PROM

log = logging.getLogger('pids.frontend')
router = APIRouter(tags=['tiempo real'])

FUENTE = 'tiempo_real'
HORAS_POR_DEFECTO = 6
MAX_HORAS = 48
TTL_TIEMPO_REAL = 20.0
CACHE = ACCESO.CacheTTL(TTL_TIEMPO_REAL)      # clave: (url, horas) -> parte de la API de acceso


def limpiar_cache() -> None:
    CACHE.limpiar()


async def desde_la_api(cliente: ACCESO.ClienteAcceso, horas: int) -> dict:
    """`ultimo_dia`, `por_hora` y `por_zona_ultima_hora` (cacheados unos segundos) más `acceso_disponible`."""
    clave = (cliente.url, horas)
    cacheado = CACHE.obtener(clave)
    if cacheado is not ACCESO.SIN_VALOR:
        return cacheado
    try:
        ultimo = await cliente.ultimo_dia(FUENTE)
        ultimas = await cliente.ultimas_horas(FUENTE, horas) if ultimo else []
    except ACCESO.ServicioNoDisponible as error:
        log.warning('Tiempo real sin la API de acceso: %s', error)
        return {'ultimo_dia': None, 'por_hora': [], 'por_zona_ultima_hora': [], 'acceso_disponible': False}
    except ACCESO.ConsultaRechazada as error:
        log.warning('La API ha rechazado una consulta interna del tiempo real: %s', error)
        return {'ultimo_dia': None, 'por_hora': [], 'por_zona_ultima_hora': [], 'acceso_disponible': True}
    return CACHE.guardar(clave, {
        'ultimo_dia': ultimo['dia'] if ultimo else None,
        'por_hora': [ACCESO.resumir_hora(hora, filas) for hora, filas in ultimas],
        'por_zona_ultima_hora': ultimas[-1][1] if ultimas else [],
        'acceso_disponible': True,
    })


@router.get('/tiempo-real')
async def tiempo_real(cfg: ConfiguracionDep, http: HttpDep,
                      horas: Annotated[int, Query(ge=1, le=MAX_HORAS, description='Horas con datos a devolver')]
                      = HORAS_POR_DEFECTO) -> dict:
    frescura, datos = await asyncio.gather(PROM.frescura_tiempo_real(http, cfg),
                                           desde_la_api(ACCESO.cliente(cfg, http), horas))
    return {'frescura': frescura, **datos}
