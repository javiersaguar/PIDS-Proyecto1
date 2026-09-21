"""Cliente de la API REST v2 de Airflow 3 para las cargas históricas (`pids_carga_historica`).

Autenticación: `POST {AIRFLOW_URL}/auth/token {"username", "password"}` devuelve un JWT (`access_token`) que va en
`Authorization: Bearer`. El token se guarda en memoria por proceso y URL y se renueva una vez cuando Airflow lo
rechaza: 401, o 403 «Invalid JWT token», que es lo que Airflow 3 responde a un token caducado.

  ejecuciones()         GET  /api/v2/dags/pids_carga_historica/dagRuns?order_by=-logical_date&limit=20
                        -> EjecucionAirflow[] (dag_run_id, estado, conf, inicio, fin)
  lanzar(mes, muestra)  POST /api/v2/dags/pids_carga_historica/dagRuns {"logical_date": null, "conf": {mes, muestra}}

`mes` se valida con `^2020-(0[1-9]|1[0-2])$` (el mismo patrón del `Param` del DAG); lo hace la ruta con Pydantic
(422). Airflow caído -> `ServicioNoDisponible`; una petición que Airflow rechaza (409, 404, 422…) -> `AirflowRechaza`
con su código y su detalle. La contraseña no se registra nunca.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from ..configuracion import Configuracion
from .acceso import ServicioNoDisponible

log = logging.getLogger('pids.frontend')

DAG = 'pids_carga_historica'
PATRON_MES = r'^2020-(0[1-9]|1[0-2])$'
LIMITE_EJECUCIONES = 20
TIEMPO_AIRFLOW = 15.0
CODIGOS_TOKEN_INVALIDO = (401, 403)

_tokens: dict[str, str] = {}       # url de Airflow -> JWT vigente


def olvidar_tokens() -> None:
    _tokens.clear()


class AirflowRechaza(Exception):
    """Airflow ha respondido 4xx a una petición ya autenticada (409 si hay conflicto, 404, 422…)."""

    def __init__(self, codigo: int, detalle: str):
        super().__init__(f'Airflow ha respondido HTTP {codigo}: {detalle}')
        self.codigo = codigo
        self.detalle = detalle


def ejecucion(run: dict) -> dict:
    """`EjecucionAirflow` del contrato a partir de un DagRun de la API v2."""
    return {
        'dag_run_id': str(run.get('dag_run_id', '')),
        'estado': str(run.get('state') or 'desconocido'),
        'conf': dict(run.get('conf') or {}),
        'inicio': run.get('start_date'),
        'fin': run.get('end_date'),
    }


def detalle_de(respuesta: httpx.Response) -> str:
    """El `detail` de un error de Airflow como texto corto (puede ser una cadena o una lista de errores)."""
    try:
        detalle = respuesta.json().get('detail')
    except (ValueError, AttributeError):
        detalle = None
    if detalle is None:
        return respuesta.text[:200] or f'HTTP {respuesta.status_code}'
    return detalle if isinstance(detalle, str) else str(detalle)[:300]


class ClienteAirflow:
    def __init__(self, http: httpx.AsyncClient, url: str, usuario: str, clave: str):
        self.http = http
        self.url = url.rstrip('/')
        self.usuario = usuario
        self.clave = clave

    async def _enviar(self, metodo: str, ruta: str, **kwargs: Any) -> httpx.Response:
        try:
            return await self.http.request(metodo, f'{self.url}{ruta}', timeout=TIEMPO_AIRFLOW, **kwargs)
        except httpx.HTTPError as error:
            raise ServicioNoDisponible('Airflow', f'no responde ({type(error).__name__})') from error

    async def token(self, renovar: bool = False) -> str:
        """El JWT vigente (cacheado por URL) o uno nuevo si `renovar` o no había ninguno."""
        if not renovar and self.url in _tokens:
            return _tokens[self.url]
        respuesta = await self._enviar('POST', '/auth/token', json={'username': self.usuario, 'password': self.clave})
        if respuesta.status_code in CODIGOS_TOKEN_INVALIDO:
            raise ServicioNoDisponible('Airflow',
                                       'no acepta las credenciales del portal (AIRFLOW_USUARIO/AIRFLOW_CLAVE)')
        if not respuesta.is_success:
            raise ServicioNoDisponible('Airflow', f'ha respondido HTTP {respuesta.status_code} al pedir el token')
        try:
            token = str(respuesta.json()['access_token'])
        except (ValueError, KeyError, TypeError) as error:
            raise ServicioNoDisponible('Airflow', 'no ha devuelto un token válido') from error
        _tokens[self.url] = token
        return token

    async def _autenticada(self, metodo: str, ruta: str, **kwargs: Any) -> httpx.Response:
        """Petición con Bearer; si Airflow rechaza el token, se renueva una vez y se repite."""
        respuesta = None
        for renovar in (False, True):
            token = await self.token(renovar=renovar)
            respuesta = await self._enviar(metodo, ruta, headers={'Authorization': f'Bearer {token}'}, **kwargs)
            if respuesta.status_code not in CODIGOS_TOKEN_INVALIDO:
                return respuesta
        raise ServicioNoDisponible('Airflow', 'rechaza el token del portal incluso recién renovado')

    def _json(self, respuesta: httpx.Response) -> Any:
        try:
            return respuesta.json()
        except ValueError as error:
            raise ServicioNoDisponible('Airflow', f'respuesta no válida (HTTP {respuesta.status_code})') from error

    async def ejecuciones(self) -> list[dict]:
        """Las últimas 20 ejecuciones del DAG, la más reciente primero."""
        respuesta = await self._autenticada('GET', f'/api/v2/dags/{DAG}/dagRuns',
                                            params={'order_by': '-logical_date', 'limit': LIMITE_EJECUCIONES})
        if respuesta.status_code != 200:
            raise ServicioNoDisponible('Airflow', f'ha respondido HTTP {respuesta.status_code} al listar ejecuciones')
        cuerpo = self._json(respuesta)
        return [ejecucion(run) for run in cuerpo.get('dag_runs', [])]

    async def lanzar(self, mes: str, muestra: bool) -> dict:
        """Crea una ejecución manual con `conf = {mes, muestra}` y devuelve la `EjecucionAirflow` creada."""
        respuesta = await self._autenticada('POST', f'/api/v2/dags/{DAG}/dagRuns',
                                            json={'logical_date': None, 'conf': {'mes': mes, 'muestra': muestra}})
        if respuesta.is_success:
            log.info('Carga histórica lanzada en Airflow (mes=%s, muestra=%s)', mes, muestra)
            return ejecucion(self._json(respuesta))
        if 400 <= respuesta.status_code < 500:
            raise AirflowRechaza(respuesta.status_code, detalle_de(respuesta))
        raise ServicioNoDisponible('Airflow', f'ha respondido HTTP {respuesta.status_code} al lanzar la carga')


def cliente(cfg: Configuracion, http: httpx.AsyncClient) -> ClienteAirflow:
    return ClienteAirflow(http, cfg.airflow_url, cfg.airflow_usuario, cfg.airflow_clave)
