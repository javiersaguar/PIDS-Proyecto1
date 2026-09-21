"""Operaciones (CONTRATOS.md §5): cargas históricas con Airflow y el simulador de tiempo real integrado.

  GET    /api/operaciones/airflow/ejecuciones            -> EjecucionAirflow[] (las últimas 20, la más reciente primero)
  POST   /api/operaciones/airflow/cargas {mes, muestra}  -> 202 EjecucionAirflow (422 si el mes no es 2020-01…2020-12)
  GET    /api/operaciones/simulacion/ficheros            -> string[] (solo los CSV de data/muestra)
  GET    /api/operaciones/simulacion                     -> Simulacion
  POST   /api/operaciones/simulacion {fichero, ritmo?, maximo?}
                                                         -> 202 Simulacion (409 si ya hay una; 400 si el fichero no vale)
  DELETE /api/operaciones/simulacion                     -> Simulacion (cancelada)

Errores de los servicios: Airflow caído -> 503 con `detail` en español (la lista de ejecuciones no admite un
`disponible: false` y un `null` rompería la tabla de la SPA: la página muestra el error con «Reintentar»); una
petición que Airflow rechaza -> 409 (conflicto) o 502 con su detalle. Nunca un 500. Las claves nunca aparecen en las
respuestas ni en los logs.

`app.py` incluye este router con `prefix='/api'` y la dependencia de sesión: las rutas van sin `/api`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..seguridad import ConfiguracionDep, HttpDep
from ..servicios import airflow as AIR
from ..servicios import simulacion as SIM
from ..servicios.acceso import ServicioNoDisponible

router = APIRouter(tags=['operaciones'])

MAX_RITMO = 5000.0


class PeticionCarga(BaseModel):
    mes: str = Field(pattern=AIR.PATRON_MES, description='Mes de 2020 (2020-01 … 2020-12)', examples=['2020-01'])
    muestra: bool = Field(default=False, description='Usar el CSV de muestra en lugar del mes completo')


class PeticionSimulacion(BaseModel):
    fichero: str = Field(min_length=1, max_length=255, examples=['yellow_tripdata_2020_muestra.csv'])
    ritmo: float = Field(default=SIM.RITMO_POR_DEFECTO, gt=0, le=MAX_RITMO, description='Viajes por segundo')
    maximo: int | None = Field(default=None, ge=1, description='Enviar como mucho estos viajes')


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


@router.post('/operaciones/airflow/cargas', status_code=202)
async def lanzar_carga(peticion: PeticionCarga, cfg: ConfiguracionDep, http: HttpDep) -> dict:
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
    return _simulador().estado.a_dict()


@router.post('/operaciones/simulacion', status_code=202)
async def iniciar_simulacion(peticion: PeticionSimulacion, cfg: ConfiguracionDep, http: HttpDep) -> dict:
    try:
        return await _simulador().iniciar(http, cfg.captura_url, cfg.captura_clave, peticion.fichero,
                                          ritmo=peticion.ritmo, maximo=peticion.maximo)
    except SIM.SimulacionActiva as error:
        raise HTTPException(status_code=409,
                            detail='Ya hay una simulación en marcha; párala antes de iniciar otra') from error
    except SIM.FicheroNoPermitido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete('/operaciones/simulacion')
async def parar_simulacion() -> dict:
    return await _simulador().parar()
