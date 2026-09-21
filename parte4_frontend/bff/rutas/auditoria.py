"""Auditoría de privacidad (CONTRATOS.md §5), leída de MongoDB con `pids_auditor` (solo lectura):

  GET /api/auditoria/resumen?horas=24                                    -> AuditoriaResumen
  GET /api/auditoria/decisiones?horas=24&resultado=&cliente=&limite=100  -> DecisionAuditada[] (límite máximo 500)
  GET /api/auditoria/cargas                                              -> Carga[]           (la más reciente primero)

Las decisiones no contienen viajes: solo la consulta pedida, quién la hizo y qué decidió el filtro (E3). El resumen
agrupa los motivos de rechazo por su tipo (el texto antes de `': '`), como `scripts/informe_auditoria.py`. MongoDB
caído -> `disponible: false` o listas vacías, con 200.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: las rutas van sin `/api`.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from ..seguridad import ConfiguracionDep
from ..servicios import auditoria as AUD

router = APIRouter(tags=['auditoría'])

MAX_HORAS = 24 * 366
MAX_LIMITE = 500
Horas = Annotated[float, Query(gt=0, le=MAX_HORAS, description='Periodo hacia atrás desde ahora, en horas')]


@router.get('/auditoria/resumen')
async def resumen(cfg: ConfiguracionDep, horas: Horas = 24) -> dict:
    return await AUD.Auditoria(cfg.auditoria_mongo_uri).resumen(horas)


@router.get('/auditoria/decisiones')
async def decisiones(cfg: ConfiguracionDep, horas: Horas = 24,
                     resultado: Annotated[str | None, Query(max_length=30)] = None,
                     cliente: Annotated[str | None, Query(max_length=60)] = None,
                     limite: Annotated[int, Query(ge=1, le=MAX_LIMITE)] = 100) -> list[dict]:
    return await AUD.Auditoria(cfg.auditoria_mongo_uri).decisiones(horas, resultado, cliente, limite)


@router.get('/auditoria/cargas')
async def cargas(cfg: ConfiguracionDep) -> list[dict]:
    return await AUD.Auditoria(cfg.auditoria_mongo_uri).cargas()
