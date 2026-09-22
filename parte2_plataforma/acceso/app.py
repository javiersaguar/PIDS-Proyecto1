"""API de acceso: la única puerta a los datos de la plataforma (la usan el chatbot, Airflow y Grafana).

Cada consulta pasa por el filtro de privacidad (parte2_plataforma/comun/privacidad.py):
  permitida    se responde
  enmascarada  se responde, con las cifras de los grupos pequeños ocultas
  rechazada    HTTP 403 con los motivos y una consulta alternativa que sí se puede responder
Todas las decisiones quedan en auditoria.decisiones (colección de solo inserción).

Rutas:
  GET  /salud, /catalogo, /zonas?texto=
  POST /consultas              consulta agregada
  POST /consultas/individual   cualquier intento de obtener viajes concretos (siempre se rechaza)
  GET  /viajes/...             ídem: no existe acceso a viajes individuales
  GET  /metrics                Prometheus (incluye agregados ya protegidos para Grafana)
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, make_asgi_app
from pydantic import BaseModel, Field

from ..comun import privacidad as P
from .repositorio import Repositorio, RepositorioMongo

log = logging.getLogger('pids.acceso')

CONSULTAS = Counter('acceso_consultas_total', 'Consultas por resultado', ['resultado', 'cliente'])
ENMASCARADOS = Counter('acceso_grupos_enmascarados_total', 'Grupos devueltos sin cifras', ['nivel'])
VIAJES_BARRIO = Gauge('publico_viajes_ultimo_dia', 'Viajes del último día publicado, por barrio (agregado protegido)',
                      ['barrio', 'fuente'])
ULTIMO_DIA = Gauge('publico_ultimo_dia_timestamp_segundos', 'Último día con datos publicados', ['fuente'])
ULTIMA_ACTUALIZACION = Gauge('publico_ultima_actualizacion_timestamp_segundos',
                             'Última escritura de Spark en los agregados de tiempo real; 0 si no hay datos', ['fuente'])
DOCUMENTOS = Gauge('publico_documentos', 'Documentos de una colección de agregados protegidos', ['coleccion', 'fuente'])
DATOS_BYTES = Gauge('publico_datos_bytes', 'Bytes de los documentos de una colección de agregados protegidos',
                    ['coleccion', 'fuente'])
INTERVALO_METRICAS = int(os.environ.get('ACCESO_INTERVALO_METRICAS', '60'))


def claves() -> dict[str, str]:
    """ACCESO_CLAVES="cliente1=clave1,cliente2=clave2" -> {clave: cliente}."""
    pares = (p.split('=', 1) for p in os.environ.get('ACCESO_CLAVES', '').split(',') if '=' in p)
    return {clave.strip(): cliente.strip() for cliente, clave in pares if clave.strip()}


async def cliente(x_api_key: Annotated[str | None, Header()] = None) -> str:
    nombre = claves().get(x_api_key or '')
    if nombre is None:
        raise HTTPException(status_code=401, detail='Falta la cabecera X-API-Key o no es válida')
    return nombre


async def _refrescar_metricas(repo: Repositorio) -> None:
    while True:
        await _refrescar_frescura(repo)
        for fuente in P.config()['fuentes']:
            with contextlib.suppress(Exception):
                dia, por_barrio = await repo.ultimo_dia_por_barrio(fuente)
                if dia is not None:
                    ULTIMO_DIA.labels(fuente).set(dia.replace(tzinfo=timezone.utc).timestamp())
                    for barrio, n in por_barrio.items():
                        VIAJES_BARRIO.labels(barrio, fuente).set(n)
        await _refrescar_inventario(repo)
        await asyncio.sleep(INTERVALO_METRICAS)


async def _refrescar_frescura(repo: Repositorio) -> None:
    try:
        instante = await repo.ultima_actualizacion_tiempo_real()
    except Exception:
        # No conservar un valor antiguo como si la lectura siguiera funcionando.
        ULTIMA_ACTUALIZACION.labels('tiempo_real').set(float('nan'))
        log.warning('No se pudo leer la frescura del tiempo real')
        return
    if instante is not None:
        instante = instante.replace(tzinfo=timezone.utc) if instante.tzinfo is None else instante
    ULTIMA_ACTUALIZACION.labels('tiempo_real').set(instante.timestamp() if instante else 0)


async def _refrescar_inventario(repo: Repositorio) -> None:
    try:
        filas = await repo.inventario()
    except Exception:
        log.warning('No se pudo leer el inventario de las colecciones publicadas')
        return
    for fila in filas:
        DOCUMENTOS.labels(fila['coleccion'], fila['fuente']).set(fila['documentos'])
        DATOS_BYTES.labels(fila['coleccion'], fila['fuente']).set(fila['bytes'])


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    if getattr(app.state, 'repo', None) is None:              # los tests inyectan uno falso
        app.state.repo = RepositorioMongo(os.environ['MONGO_URI'])
    tarea = asyncio.create_task(_refrescar_metricas(app.state.repo))
    try:
        yield
    finally:
        tarea.cancel()
        await app.state.repo.cerrar()


app = FastAPI(title='PIDS · API de acceso', version='0.1.0', lifespan=ciclo_de_vida)
app.mount('/metrics', make_asgi_app())


def repo(request: Request) -> Repositorio:
    return request.app.state.repo


async def _auditar(r: Repositorio, quien: str, consulta: dict, decision: P.Decision, **extra) -> None:
    CONSULTAS.labels(decision.resultado.value, quien).inc()
    await r.auditar({
        'instante': datetime.now(timezone.utc),
        'componente': 'acceso',
        'cliente': quien,
        'consulta': consulta,
        'resultado': decision.resultado.value,
        'motivos': decision.motivos,
        'alternativa': decision.alternativa.model_dump(mode='json') if decision.alternativa else None,
        'version_reglas': P.config()['version'],
        **extra,
    })


def _rechazo(decision: P.Decision) -> JSONResponse:
    return JSONResponse(status_code=403, content=decision.model_dump(mode='json'))


@app.get('/salud')
async def salud() -> dict:
    return {'estado': 'ok'}


@app.get('/catalogo')
async def catalogo(r: Annotated[Repositorio, Depends(repo)], _: Annotated[str, Depends(cliente)]) -> dict:
    cfg = P.config()
    return {
        'k_minimo': cfg['k_minimo'],
        'max_dias_por_consulta': cfg['max_dias_por_consulta'],
        'metricas': cfg['metricas'],
        'niveles': {n: {'descripcion': v['descripcion'], 'dimensiones': v['dimensiones']}
                    for n, v in cfg['niveles'].items()},
        'fuentes': list(cfg['fuentes']),
        'barrios': await r.barrios(),
    }


@app.get('/zonas')
async def zonas(r: Annotated[Repositorio, Depends(repo)], _: Annotated[str, Depends(cliente)],
                texto: str | None = None) -> list[dict]:
    return await r.zonas(texto[:50] if texto else None)


class Respuesta(BaseModel):
    resultado: P.Resultado
    consulta: P.Consulta
    filas: list[dict]
    grupos_enmascarados: int
    truncada: bool
    nota: str


@app.post('/consultas', response_model=Respuesta, responses={403: {'model': P.Decision}})
async def consultar(consulta: P.Consulta, r: Annotated[Repositorio, Depends(repo)],
                    quien: Annotated[str, Depends(cliente)]):
    pedida = consulta.model_dump(mode='json')
    decision = P.evaluar(consulta)
    if decision.resultado == P.Resultado.RECHAZADA:
        await _auditar(r, quien, pedida, decision)
        return _rechazo(decision)

    maximo = P.config()['max_filas_por_respuesta']
    filas = await r.buscar(consulta, maximo + 1)
    truncada = len(filas) > maximo
    filas, ocultas = P.enmascarar(filas[:maximo], [m for m in consulta.metricas if m != 'n_viajes'])
    ENMASCARADOS.labels(consulta.nivel).inc(ocultas)
    final = P.Decision(resultado=P.resultado_final(ocultas),
                       motivos=[f'{ocultas} grupos con menos de {P.config()["k_minimo"]} viajes'] if ocultas else [])
    await _auditar(r, quien, pedida, final, filas_devueltas=len(filas), grupos_enmascarados=ocultas)
    return Respuesta(
        resultado=final.resultado, consulta=consulta, filas=filas, grupos_enmascarados=ocultas,
        truncada=truncada,
        nota='Los grupos enmascarados no se suman a ningún total: ocultarlos no serviría si se pudieran '
             'deducir por diferencia.')


class PeticionIndividual(BaseModel):
    descripcion: str = Field(max_length=500)


@app.post('/consultas/individual', status_code=403, response_model=P.Decision)
async def consulta_individual(peticion: PeticionIndividual, r: Annotated[Repositorio, Depends(repo)],
                              quien: Annotated[str, Depends(cliente)]):
    decision = P.rechazo_individual(peticion.descripcion)
    await _auditar(r, quien, {'individual': peticion.descripcion}, decision)
    return _rechazo(decision)


@app.api_route('/viajes/{resto:path}', methods=['GET', 'POST'], status_code=403, include_in_schema=False)
async def viajes_individuales(resto: str, r: Annotated[Repositorio, Depends(repo)],
                              quien: Annotated[str, Depends(cliente)]):
    decision = P.rechazo_individual(f'/viajes/{resto}')
    await _auditar(r, quien, {'ruta': f'/viajes/{resto}'}, decision)
    return _rechazo(decision)
