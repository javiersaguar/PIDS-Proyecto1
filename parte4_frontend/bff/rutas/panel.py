"""`GET /api/panel` -> `Panel` (CONTRATOS.md §5): la portada del portal en una sola respuesta.

- `ultimo_dia.{historico,tiempo_real}`: el último día con datos de 2020, obtenido con consultas normales
  `dia_barrio` a la API de acceso (diciembre y hacia atrás, mes a mes; fuente correspondiente). Solo se suman los
  grupos visibles (`suprimido: false`); los enmascarados se cuentan en `grupos_enmascarados`, nunca se suman.
- `frescura_tiempo_real`, `consultas_24h` y `servicios`: de Prometheus (más `GET /salud` de las APIs).
- `enlaces`: los del menú (`cfg.enlaces`).

Un servicio caído no rompe la portada: `null`/`prometheus_disponible: false`/`acceso_disponible: false` y 200.
`acceso_disponible` no está en el contrato: distingue «la API no responde» de «no hay datos publicados».

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: la ruta va sin `/api`.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import acceso as ACCESO
from ..servicios import prometheus as PROM

log = logging.getLogger('pids.frontend')
router = APIRouter(tags=['panel'])

FUENTES = ('historico', 'tiempo_real')


async def ultimo_dia_seguro(cliente: ACCESO.ClienteAcceso, fuente: str) -> tuple[dict | None, bool]:
    """(`UltimoDia` o None, ¿la API ha respondido?). Un rechazo de una consulta interna cuenta como «sin datos»."""
    try:
        return await cliente.ultimo_dia(fuente), True
    except ACCESO.ServicioNoDisponible as error:
        log.warning('Panel sin último día de %s: %s', fuente, error)
        return None, False
    except ACCESO.ConsultaRechazada as error:
        log.warning('La API ha rechazado la consulta interna del último día de %s: %s', fuente, error)
        return None, True


@router.get('/panel')
async def panel(cfg: ConfiguracionDep, http: HttpDep) -> dict:
    cliente = ACCESO.cliente(cfg, http)
    estado, *ultimos = await asyncio.gather(PROM.estado_plataforma(http, cfg),
                                            *(ultimo_dia_seguro(cliente, fuente) for fuente in FUENTES))
    return {
        'ultimo_dia': {fuente: ultimo for fuente, (ultimo, _) in zip(FUENTES, ultimos, strict=True)},
        'frescura_tiempo_real': estado['frescura_tiempo_real'],
        'consultas_24h': estado['consultas_24h'],
        'servicios': estado['servicios'],
        'enlaces': dict(cfg.enlaces),
        'prometheus_disponible': estado['prometheus_disponible'],
        'acceso_disponible': all(disponible for _, disponible in ultimos),
    }
