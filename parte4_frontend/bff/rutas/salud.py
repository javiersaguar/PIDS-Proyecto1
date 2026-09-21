"""`GET /api/salud`: comprobación de vida del BFF (la usa el healthcheck de Compose). Sin sesión."""
from __future__ import annotations

from fastapi import APIRouter

from ..seguridad import ConfiguracionDep

router = APIRouter(tags=['salud'])


@router.get('/salud')
async def salud(cfg: ConfiguracionDep) -> dict:
    return {'estado': 'ok', 'spa_construida': (cfg.dist_spa / 'index.html').is_file()}
