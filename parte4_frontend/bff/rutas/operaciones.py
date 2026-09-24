"""Operaciones (CONTRATOS.md §5): cargas históricas con Airflow y el simulador de tiempo real integrado.

  GET    /api/operaciones/airflow/ejecuciones            -> EjecucionAirflow[] (las últimas 20, la más reciente primero)
  GET    /api/operaciones/airflow/muestra                 -> {bloqueada, motivo}
  POST   /api/operaciones/airflow/cargas {mes, muestra}  -> 202 EjecucionAirflow (422 si el mes no es 2020-01…2020-12;
                                                            409 si muestra=true y ya hay una carga que no es la muestra)
  GET    /api/operaciones/simulacion/ficheros            -> string[] (solo los CSV de data/muestra)
  GET    /api/operaciones/simulacion                     -> Simulacion
  POST   /api/operaciones/simulacion {fichero, ritmo?, maximo?, sinteticos?, semilla?}
                                                         -> 202 Simulacion (409 si ya hay una; 400 si el fichero no vale)
  DELETE /api/operaciones/simulacion                     -> Simulacion (cancelada)
  GET    /api/operaciones/captura                        -> qué hay preparado para la captura en directo
  POST   /api/operaciones/captura {velocidad?, desde?}   -> 202 Simulacion con modo 'directo' (409 si ya hay una o si
                                                            no queda nada que enviar; 503 si la API de acceso no responde)
  DELETE /api/operaciones/captura                        -> Simulacion (parada); igual que DELETE …/simulacion

Errores de los servicios: Airflow caído -> 503 con `detail` en español (la lista de ejecuciones no admite un
`disponible: false` y un `null` rompería la tabla de la SPA: la página muestra el error con «Reintentar»); una
petición que Airflow rechaza -> 409 (conflicto) o 502 con su detalle. Nunca un 500. Las claves nunca aparecen en las
respuestas ni en los logs.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: las rutas van sin `/api`.
"""
from __future__ import annotations

import asyncio
import importlib.util
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from parte2_plataforma.simulador import directo as DIRECTO

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import acceso as ACCESO
from ..servicios import airflow as AIR
from ..servicios import simulacion as SIM
from ..servicios.acceso import ServicioNoDisponible
from ..servicios.auditoria import cliente_mongo

router = APIRouter(tags=['operaciones'])


def _reglas_muestra():
    """La misma regla que la primera tarea del DAG (`proteger_historico.py`), sin importar Airflow."""
    ruta = Path(__file__).resolve().parents[3] / 'parte2_plataforma' / 'airflow' / 'dags' / 'proteger_historico.py'
    spec = importlib.util.spec_from_file_location('proteger_historico', ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


REGLAS_MUESTRA = _reglas_muestra()


def _cargas_registradas(uri: str) -> list[dict]:
    return list(cliente_mongo(uri)['auditoria']['cargas'].find({}, {'lote': 1, 'entrada': 1}))

MAX_RITMO = 5000.0


class PeticionCarga(BaseModel):
    mes: str = Field(pattern=AIR.PATRON_MES, description='Mes de 2020 (2020-01 … 2020-12)', examples=['2020-01'])
    muestra: bool = Field(default=False, description='Usar el CSV de muestra en lugar del mes completo')


class PeticionSimulacion(BaseModel):
    fichero: str = Field(min_length=1, max_length=255, examples=['yellow_tripdata_2020_muestra.csv'])
    ritmo: float = Field(default=SIM.RITMO_POR_DEFECTO, gt=0, le=MAX_RITMO, description='Viajes por segundo')
    maximo: int | None = Field(default=None, ge=1, description='Enviar como mucho estos viajes')
    sinteticos: int | None = Field(default=None, ge=1, le=SIM.MAXIMO_SINTETICOS,
                                   description='Generar estos viajes a partir del fichero en vez de enviarlo entero')
    semilla: int | None = Field(default=None, description='Semilla de la generación, para repetirla igual')


class PeticionCaptura(BaseModel):
    velocidad: float = Field(default=DIRECTO.VELOCIDAD_POR_DEFECTO, ge=1, le=DIRECTO.VELOCIDAD_MAXIMA,
                             description='Segundos de 2020 por segundo real (60 = una hora por minuto)')
    desde: datetime | None = Field(default=None, description='Hora de 2020 por la que empezar; por defecto, donde se '
                                   'quedó. Antes de la última publicada, Spark descartaría los viajes')


def _simulador() -> SIM.Simulador:
    return SIM.SIMULADOR       # atributo del módulo para que los tests puedan sustituirlo


# --- Airflow -----------------------------------------------------------------------------------------------

def airflow_no_disponible(error: ServicioNoDisponible) -> HTTPException:
    return HTTPException(status_code=503, detail=f'Airflow no está disponible: {error.detalle}')


@router.get('/operaciones/airflow/ejecuciones')
async def ejecuciones(cfg: ConfiguracionDep, http: HttpDep) -> list[dict]:
    try:
        return await AIR.cliente(cfg, http).ejecuciones()
    except ServicioNoDisponible as error:
        raise airflow_no_disponible(error) from error


@router.get('/operaciones/airflow/muestra')
async def estado_muestra(cfg: ConfiguracionDep) -> dict:
    """Si la casilla de la muestra debe quedar apagada, y por qué."""
    try:
        cargas = await asyncio.to_thread(_cargas_registradas, cfg.auditoria_mongo_uri)
    except PyMongoError:
        return {'bloqueada': True, 'motivo': REGLAS_MUESTRA.MENSAJE_SIN_COMPROBAR}
    motivo = REGLAS_MUESTRA.motivo_si_bloqueada(cargas)
    return {'bloqueada': motivo is not None, 'motivo': motivo}


@router.post('/operaciones/airflow/cargas', status_code=202)
async def lanzar_carga(peticion: PeticionCarga, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    if peticion.muestra:
        try:
            cargas = await asyncio.to_thread(_cargas_registradas, cfg.auditoria_mongo_uri)
        except PyMongoError as error:
            raise HTTPException(status_code=503, detail=REGLAS_MUESTRA.MENSAJE_SIN_COMPROBAR) from error
        motivo = REGLAS_MUESTRA.motivo_si_bloqueada(cargas)
        if motivo:
            raise HTTPException(status_code=409, detail=motivo)
    try:
        return await AIR.cliente(cfg, http).lanzar(peticion.mes, peticion.muestra)
    except AIR.AirflowRechaza as error:
        codigo = 409 if error.codigo == 409 else 502
        raise HTTPException(status_code=codigo, detail=f'Airflow no ha aceptado la carga: {error.detalle}') from error
    except ServicioNoDisponible as error:
        raise airflow_no_disponible(error) from error


# --- simulador ---------------------------------------------------------------------------------------------

@router.get('/operaciones/simulacion/ficheros')
async def ficheros_simulacion() -> list[str]:
    return _simulador().ficheros()


@router.get('/operaciones/simulacion')
async def estado_simulacion() -> dict:
    return _simulador().estado_actual()


@router.post('/operaciones/simulacion', status_code=202)
async def iniciar_simulacion(peticion: PeticionSimulacion, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    cliente = ACCESO.cliente(cfg, http)

    async def consultar(consulta: dict) -> list[dict]:
        """Para fechar los viajes donde el tiempo real los acepte (`Simulador._dia_tiempo_real`)."""
        codigo, cuerpo = await cliente.consultar(consulta)
        return cuerpo.get('filas', []) if codigo == 200 else []

    try:
        return await _simulador().iniciar(http, cfg.captura_url, cfg.captura_clave, peticion.fichero,
                                          ritmo=peticion.ritmo, maximo=peticion.maximo,
                                          sinteticos=peticion.sinteticos, semilla=peticion.semilla,
                                          consultar=consultar)
    except SIM.SimulacionActiva as error:
        raise HTTPException(status_code=409,
                            detail='Ya hay una simulación en marcha; párala antes de iniciar otra') from error
    except SIM.FicheroNoPermitido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete('/operaciones/simulacion')
async def parar_simulacion() -> dict:
    return await _simulador().parar()


# --- captura en directo -----------------------------------------------------------------------------------------

@router.get('/operaciones/captura')
async def info_captura() -> dict:
    return _simulador().info_directo()


@router.post('/operaciones/captura', status_code=202)
async def iniciar_captura(peticion: PeticionCaptura, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    cliente = ACCESO.cliente(cfg, http)

    async def consultar(consulta: dict) -> list[dict]:
        codigo, cuerpo = await cliente.consultar(consulta)
        return cuerpo.get('filas', []) if codigo == 200 else []

    try:
        return await _simulador().iniciar_directo(http, cfg.captura_url, cfg.captura_clave, consultar,
                                                  velocidad=peticion.velocidad, desde=peticion.desde)
    except SIM.SimulacionActiva as error:
        raise HTTPException(status_code=409,
                            detail='Ya hay una simulación en marcha; párala antes de capturar') from error
    except DIRECTO.SinDatos as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ServicioNoDisponible as error:
        raise HTTPException(status_code=503,
                            detail=f'No se sabe por dónde seguir: {error.detalle}') from error


@router.delete('/operaciones/captura')
async def parar_captura() -> dict:
    return await _simulador().parar()
