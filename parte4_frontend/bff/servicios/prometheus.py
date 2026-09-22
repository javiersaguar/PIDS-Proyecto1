"""Estado de la plataforma para el panel: `up` por job, frescura del tiempo real y consultas de 24 h.

Prometheus solo aporta estado, frescura y contadores (CONTRATOS.md §5): ninguna cifra de viajes del portal sale de
aquí, todas pasan por la API de acceso. Consultas instantáneas a `GET {PROMETHEUS_URL}/api/v1/query?query=…`:

  up                                                                  -> `Servicio[]` (estado por job de prometheus.yml)
  max(publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"}) -> frescura (0/NaN = aún no hay datos -> null)
  sum by (resultado) (increase(acceso_consultas_total[24h]))          -> consultas de las últimas 24 h por resultado

Además el BFF comprueba directamente `GET /salud` de las APIs de acceso y captura: si Prometheus está caído, es lo
único que puede decir de ellas (el resto de servicios queda `desconocido`); y si está levantado, la comprobación
directa manda, porque es la que refleja si el portal puede llegar a ellas ahora mismo.

Prometheus caído -> `prometheus_disponible: false`, frescura `null`, `consultas_24h: null`; nunca un 500.
"""
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Any

import httpx

from ..configuracion import Configuracion
from .acceso import ServicioNoDisponible

log = logging.getLogger('pids.frontend')

TIEMPO_PROMETHEUS = 5.0            # segundos por consulta
TIEMPO_SALUD = 3.0                 # segundos para GET /salud de una API

CONSULTA_UP = 'up'
# max(): la API de acceso son dos réplicas (T09) y las dos publican el mismo valor
CONSULTA_FRESCURA = 'max(publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"})'
CONSULTA_24H = 'sum by (resultado) (increase(acceso_consultas_total[24h]))'
RESULTADOS = ('permitida', 'enmascarada', 'rechazada')

# job de prometheus.yml -> (nombre legible, clave del enlace en cfg.enlaces o None). En este orden se muestran.
JOBS: dict[str, tuple[str, str | None]] = {
    'acceso': ('API de acceso', 'api_acceso'),
    'captura': ('API de captura', 'api_captura'),
    'redpanda': ('Redpanda (cola de eventos)', None),
    's3': ('Almacenamiento S3', None),
    'spark-master': ('Spark · máster', 'spark'),
    'spark-workers': ('Spark · workers', None),
    'spark-aplicaciones': ('Spark · aplicaciones', None),
    'prometheus': ('Prometheus', None),
}
FRESCURA_VACIA: dict[str, Any] = {'instante': None, 'segundos': None}


# --- lógica pura -------------------------------------------------------------------------------------------

def valor(muestra: dict) -> float | None:
    """El valor numérico de una muestra instantánea de Prometheus (`value: [instante, "texto"]`); NaN -> None."""
    try:
        numero = float(muestra['value'][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return None if math.isnan(numero) else numero


def estados_por_job(vector_up: list[dict]) -> dict[str, str]:
    """`ok` si todas las instancias del job responden, `caido` si alguna no."""
    estados: dict[str, str] = {}
    for muestra in vector_up:
        job = muestra.get('metric', {}).get('job')
        if not job:
            continue
        arriba = valor(muestra) == 1
        estados[job] = 'caido' if estados.get(job) == 'caido' or not arriba else 'ok'
    return estados


def servicios(vector_up: list[dict] | None, saludes: dict[str, bool], enlaces: dict[str, str]) -> list[dict]:
    """`Servicio[]`: los jobs conocidos en su orden y, detrás, cualquier otro que Prometheus sondee.

    `vector_up` es None si Prometheus no responde: todo `desconocido`, salvo las APIs comprobadas por `/salud`
    y el propio Prometheus, que queda `caido`.
    """
    estados = estados_por_job(vector_up or [])
    if vector_up is None:
        estados['prometheus'] = 'caido'
    for job, viva in saludes.items():
        estados[job] = 'ok' if viva else 'caido'
    jobs = list(JOBS) + sorted(j for j in estados if j not in JOBS)
    salida = []
    for job in jobs:
        nombre, clave_enlace = JOBS.get(job, (job, None))
        servicio = {'nombre': nombre, 'job': job, 'estado': estados.get(job, 'desconocido')}
        if clave_enlace and enlaces.get(clave_enlace):
            servicio['enlace'] = enlaces[clave_enlace]
        salida.append(servicio)
    return salida


def frescura(vector: list[dict] | None) -> dict:
    """`{instante, segundos}` desde la última escritura de Spark en el tiempo real; sin datos (0/NaN) -> nulos."""
    if not vector:
        return dict(FRESCURA_VACIA)
    muestra = vector[0]
    marca = valor(muestra)
    if not marca or marca <= 0:
        return dict(FRESCURA_VACIA)
    try:
        evaluado = float(muestra['value'][0])
    except (KeyError, IndexError, TypeError, ValueError):
        evaluado = datetime.now(timezone.utc).timestamp()
    instante = datetime.fromtimestamp(marca, tz=timezone.utc)
    return {'instante': instante.isoformat(), 'segundos': max(0, int(evaluado - marca))}


def consultas_24h(vector: list[dict]) -> dict[str, int]:
    """`increase()` devuelve reales extrapolados: se redondean. Los resultados sin muestras cuentan 0."""
    cuentas = {resultado: 0 for resultado in RESULTADOS}
    for muestra in vector:
        resultado = muestra.get('metric', {}).get('resultado')
        numero = valor(muestra)
        if resultado and numero is not None:
            cuentas[resultado] = max(0, round(numero))
    return cuentas


# --- clientes ----------------------------------------------------------------------------------------------

class ClientePrometheus:
    def __init__(self, http: httpx.AsyncClient, url: str):
        self.http = http
        self.url = url.rstrip('/')

    async def instantanea(self, expresion: str) -> list[dict]:
        """El vector de resultados de una consulta instantánea; `ServicioNoDisponible` si Prometheus no responde."""
        try:
            respuesta = await self.http.get(f'{self.url}/api/v1/query', params={'query': expresion},
                                            timeout=TIEMPO_PROMETHEUS)
        except httpx.HTTPError as error:
            raise ServicioNoDisponible('Prometheus', f'no responde ({type(error).__name__})') from error
        if respuesta.status_code != 200:
            raise ServicioNoDisponible('Prometheus', f'ha respondido HTTP {respuesta.status_code}')
        try:
            cuerpo = respuesta.json()
            if cuerpo.get('status') != 'success':
                raise ServicioNoDisponible('Prometheus', f'consulta fallida ({cuerpo.get("errorType", "error")})')
            return list(cuerpo['data']['result'])
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise ServicioNoDisponible('Prometheus', 'respuesta no válida') from error


async def salud(http: httpx.AsyncClient, url: str) -> bool:
    """¿Responde `GET {url}/salud` con `{"estado": "ok"}`? Cualquier fallo cuenta como caída."""
    try:
        respuesta = await http.get(f'{url.rstrip("/")}/salud', timeout=TIEMPO_SALUD)
        return respuesta.status_code == 200 and respuesta.json().get('estado') == 'ok'
    except (httpx.HTTPError, ValueError, AttributeError):
        return False


async def _segura(corrutina) -> list[dict] | None:
    """Una consulta a Prometheus que puede fallar: None en vez de excepción (solo `ServicioNoDisponible`)."""
    try:
        return await corrutina
    except ServicioNoDisponible as error:
        log.warning('%s', error)
        return None


async def frescura_tiempo_real(http: httpx.AsyncClient, cfg: Configuracion) -> dict:
    """Solo la frescura (la usa /tiempo-real); nulos si Prometheus no responde."""
    return frescura(await _segura(ClientePrometheus(http, cfg.prometheus_url).instantanea(CONSULTA_FRESCURA)))


async def estado_plataforma(http: httpx.AsyncClient, cfg: Configuracion) -> dict:
    """Todo lo que el panel toma de Prometheus y de `/salud`, en paralelo:

    {prometheus_disponible, servicios, frescura_tiempo_real, consultas_24h}
    """
    prometheus = ClientePrometheus(http, cfg.prometheus_url)
    vector_up, vector_frescura, vector_24h, acceso_viva, captura_viva = await asyncio.gather(
        _segura(prometheus.instantanea(CONSULTA_UP)),
        _segura(prometheus.instantanea(CONSULTA_FRESCURA)),
        _segura(prometheus.instantanea(CONSULTA_24H)),
        salud(http, cfg.acceso_url),
        salud(http, cfg.captura_url),
    )
    return {
        'prometheus_disponible': vector_up is not None,
        'servicios': servicios(vector_up, {'acceso': acceso_viva, 'captura': captura_viva}, cfg.enlaces),
        'frescura_tiempo_real': frescura(vector_frescura),
        'consultas_24h': consultas_24h(vector_24h) if vector_24h is not None else None,
    }
