"""`POST /api/consultas`: el explorador de agregados, reenviado tal cual a `POST /consultas` de la API de acceso.

El cuerpo es la misma `Consulta` de `parte2_plataforma.comun.privacidad` (se importa para validarla y documentarla)
y la respuesta es la de la API con su código: 200 `Respuesta`, 403 `Decision` (motivos y alternativa) o 422 de
validación. El BFF no relaja ni filtra nada: el filtro de privacidad está en la API y las decisiones quedan en su
auditoría con el cliente `frontend`. Si la API no responde, 503 con el motivo en español.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: la ruta va sin `/api`.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from parte2_plataforma.comun import privacidad as P

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import acceso as ACCESO
from .catalogo import error_acceso

router = APIRouter(tags=['consultas'])


@router.post('/consultas', responses={200: {'description': 'Respuesta de la API de acceso'},
                                      403: {'description': 'Decision de la API de acceso (rechazada)'},
                                      503: {'description': 'La API de acceso no está disponible'}})
async def consultar(consulta: P.Consulta, cfg: ConfiguracionDep, http: HttpDep) -> JSONResponse:
    try:
        codigo, cuerpo = await ACCESO.cliente(cfg, http).consultar(consulta.model_dump(mode='json'))
    except ACCESO.ServicioNoDisponible as error:
        raise error_acceso(error) from error
    return JSONResponse(status_code=codigo, content=cuerpo)
