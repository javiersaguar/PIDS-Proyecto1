"""La SPA construida (`parte4_frontend/web/dist`) servida por el propio FastAPI.

- `/assets/*` son ficheros con hash en el nombre: se sirven con caché inmutable de un año.
- Cualquier otra ruta que no empiece por `/api` devuelve `index.html` (el enrutador de la SPA decide), salvo que
  exista un fichero con ese nombre en `dist` (favicon, etc.).
- Si `dist` no existe (desarrollo con `npm run dev`, o imagen sin construir), `GET /` responde un JSON con las
  instrucciones para construirla y el resto de rutas un 404.

Se monta después de los routers de `/api` para que nunca tape una ruta de la API: un `/api/lo-que-sea`
desconocido sigue siendo un 404 JSON, no la SPA.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

CACHE_INMUTABLE = 'public, max-age=31536000, immutable'
CACHE_SIN = 'no-cache'
INSTRUCCIONES = {
    'detail': 'La SPA no está construida: este proceso solo sirve la API en /api.',
    'como_construirla': 'cd parte4_frontend/web && npm ci && npm run build',
    'en_desarrollo': 'cd parte4_frontend/web && npm run dev   (http://localhost:5173, proxy de /api a este puerto)',
    'api': {'salud': '/api/salud', 'documentacion': '/api/docs'},
}


class EstaticosInmutables(StaticFiles):
    """`StaticFiles` que marca todo como inmutable (los nombres llevan el hash del contenido)."""

    def file_response(self, full_path: str | os.PathLike[str], stat_result: os.stat_result, scope: Scope,
                      status_code: int = 200):
        respuesta = super().file_response(full_path, stat_result, scope, status_code)
        respuesta.headers['Cache-Control'] = CACHE_INMUTABLE
        return respuesta


def spa_construida(dist: Path) -> bool:
    return (dist / 'index.html').is_file()


def fichero_de_dist(dist: Path, ruta: str) -> Path | None:
    """El fichero de `dist` que corresponde a la ruta, o None si no existe o intenta salirse de `dist`."""
    if not ruta or ruta.endswith('/'):
        return None
    candidato = (dist / ruta).resolve()
    if dist.resolve() not in candidato.parents or not candidato.is_file():
        return None
    return candidato


def montar_estaticos(app: FastAPI, dist: Path) -> None:
    if not spa_construida(dist):
        @app.get('/', include_in_schema=False)
        async def sin_spa() -> JSONResponse:
            return JSONResponse(INSTRUCCIONES, status_code=200)
        return

    indice = dist / 'index.html'
    if (dist / 'assets').is_dir():
        app.mount('/assets', EstaticosInmutables(directory=dist / 'assets'), name='assets')

    @app.get('/{ruta:path}', include_in_schema=False)
    async def spa(ruta: str) -> FileResponse:
        if ruta == 'api' or ruta.startswith('api/'):
            raise HTTPException(status_code=404, detail='Recurso no encontrado')
        fichero = fichero_de_dist(dist, ruta)
        if fichero is not None:
            return FileResponse(fichero, headers={'Cache-Control': CACHE_SIN})
        return FileResponse(indice, media_type='text/html', headers={'Cache-Control': CACHE_SIN})
