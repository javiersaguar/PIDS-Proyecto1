"""Cliente de la API de acceso para el BFF: la única forma que tiene el portal de ver datos (E3).

Todas las cifras del portal (explorador, panel, tiempo real) salen de `POST /consultas` de la API de acceso, con
la clave del cliente `frontend` y su filtro de privacidad delante: el BFF no consulta `publico` en MongoDB. Aquí
conviven el cliente HTTP (entrada/salida) y la lógica pura que resume sus respuestas (troceo del rango, último
día con datos, últimas horas con datos, sumas de grupos visibles), que se prueba sin red.

Dos reglas que no se relajan:
  - `POST /consultas` se reenvía tal cual y se devuelve el mismo código y el mismo cuerpo (200 `Respuesta`,
    403 `Decision`, 422 de validación).
  - Solo se suman los grupos visibles (`suprimido: false`). Los enmascarados se cuentan, nunca se suman: un total
    que los incluyera revelaría por diferencia justo lo que se ha ocultado.

Si la API no responde (o responde algo que no es una decisión) se lanza `ServicioNoDisponible`, que las rutas
convierten en `null`/`disponible: false` o en un 503 con `detail` en español; nunca en un 500. La excepción es
común a todos los clientes de `servicios/` (Prometheus, Airflow, auditoría la importan de aquí).

Cada consulta a la API queda en `auditoria.decisiones` con el cliente `frontend`; por eso el catálogo, las zonas y
las respuestas de un mes entero se guardan un rato en memoria (`CacheTTL`): lo cacheado ya salió con el filtro de
privacidad aplicado, así que no cambia ningún resultado.
"""
from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Hashable, Iterable
from datetime import datetime, timedelta
from typing import Any

import httpx

from ..configuracion import Configuracion

log = logging.getLogger('pids.frontend')

ANIO_DATOS = 2020                  # los datos publicados son de todo 2020 (CONTRATOS.md §8)
MAX_DIAS_POR_CONSULTA = 31         # config/privacidad.json: rango máximo por consulta; por encima se trocea
HORAS_DEL_DIA = 24
MAX_DIAS_RECORRIDOS = 3            # días con datos que se revisan, como mucho, buscando las últimas N horas
TIEMPO_CONSULTA = 20.0             # segundos por petición a la API
TTL_CATALOGO = 600.0               # catálogo y zonas: 10 minutos
TTL_MES = 60.0                     # respuesta `dia_barrio` de un mes entero (con o sin datos): 1 minuto, para que el
                                   # tiempo real recién simulado aparezca pronto sin repetir los 12 meses en cada carga


class ServicioNoDisponible(Exception):
    """Un servicio externo no responde o responde algo inesperado. Ni `servicio` ni `detalle` llevan claves."""

    def __init__(self, servicio: str, detalle: str):
        super().__init__(f'{servicio}: {detalle}')
        self.servicio = servicio
        self.detalle = detalle


class ConsultaRechazada(Exception):
    """La API ha rechazado (403) una consulta interna del BFF.

    No debería ocurrir: las consultas del panel y del tiempo real van alineadas a su granularidad y dentro del
    rango máximo. Si ocurre (un cambio de reglas, un error de programación) la ruta lo trata como «sin datos».
    """

    def __init__(self, decision: dict):
        super().__init__('; '.join(decision.get('motivos', [])) or 'consulta rechazada')
        self.decision = decision


# --- caché en memoria ----------------------------------------------------------------------------------------

SIN_VALOR = object()


class CacheTTL:
    """Caché por proceso con caducidad por entrada. `obtener` devuelve `SIN_VALOR` si no hay nada vigente."""

    def __init__(self, segundos: float):
        self.segundos = segundos
        self._datos: dict[Hashable, tuple[float, Any]] = {}

    def obtener(self, clave: Hashable) -> Any:
        entrada = self._datos.get(clave)
        if entrada is None:
            return SIN_VALOR
        caducidad, valor = entrada
        if caducidad <= time.monotonic():
            del self._datos[clave]
            return SIN_VALOR
        return valor

    def guardar(self, clave: Hashable, valor: Any, segundos: float | None = None) -> Any:
        self._datos[clave] = (time.monotonic() + (self.segundos if segundos is None else segundos), valor)
        return valor

    def limpiar(self) -> None:
        self._datos.clear()


CACHE_CATALOGO = CacheTTL(TTL_CATALOGO)      # clave: (url, 'catalogo') o (url, 'zonas', texto)
CACHE_MESES = CacheTTL(TTL_MES)              # clave: (url, fuente, año, mes) -> filas `dia_barrio` del mes


def limpiar_caches() -> None:
    """Para los tests: que una prueba no vea lo que cacheó la anterior."""
    CACHE_CATALOGO.limpiar()
    CACHE_MESES.limpiar()


# --- lógica pura -------------------------------------------------------------------------------------------

def iso(momento: datetime) -> str:
    """Fecha y hora sin zona, como las espera la API (`2020-01-15T08:00:00`)."""
    return momento.strftime('%Y-%m-%dT%H:%M:%S')


def fecha(texto: Any) -> datetime | None:
    """El `dia`/`hora` de una fila (ISO) como datetime, o None si no se puede interpretar."""
    try:
        return datetime.fromisoformat(str(texto))
    except (TypeError, ValueError):
        return None


Ventana = tuple[datetime, datetime]


def trocear(desde: datetime, hasta: datetime, maximo_dias: int = MAX_DIAS_POR_CONSULTA) -> list[Ventana]:
    """Ventanas consecutivas de como mucho `maximo_dias` que cubren [desde, hasta)."""
    if hasta <= desde:
        return []
    paso = timedelta(days=maximo_dias)
    ventanas, inicio = [], desde
    while inicio < hasta:
        fin = min(inicio + paso, hasta)
        ventanas.append((inicio, fin))
        inicio = fin
    return ventanas


def visible(fila: dict) -> bool:
    """Un grupo se suma solo si la API lo marcó como no suprimido y trae una cifra (no `"oculto"`)."""
    return not fila.get('suprimido') and isinstance(fila.get('n_viajes'), (int, float))


def sumar_visibles(filas: Iterable[dict]) -> tuple[int, int]:
    """(suma de `n_viajes` de los grupos visibles, número de grupos enmascarados)."""
    total, enmascarados = 0, 0
    for fila in filas:
        if visible(fila):
            total += int(fila['n_viajes'])
        else:
            enmascarados += 1
    return total, enmascarados


def agrupar(filas: Iterable[dict], campo: str) -> dict[str, list[dict]]:
    """Filas por valor de `campo` (`dia` u `hora`), con las claves en orden ascendente."""
    grupos: dict[str, list[dict]] = {}
    for fila in filas:
        grupos.setdefault(str(fila.get(campo)), []).append(fila)
    return dict(sorted(grupos.items()))


def resumir_dia(dia: str, filas: Iterable[dict]) -> dict:
    """`UltimoDia` del contrato: viajes por barrio y total, solo de los grupos visibles; los enmascarados, contados."""
    por_barrio: dict[str, int] = {}
    enmascarados = 0
    for fila in filas:
        if visible(fila):
            barrio = fila.get('barrio_origen') or 'desconocido'
            por_barrio[barrio] = por_barrio.get(barrio, 0) + int(fila['n_viajes'])
        else:
            enmascarados += 1
    return {'dia': dia, 'por_barrio': por_barrio, 'total': sum(por_barrio.values()),
            'grupos_enmascarados': enmascarados}


def resumir_hora(hora: str, filas: list[dict]) -> dict:
    """Una entrada de `TiempoReal.por_hora`: viajes visibles, grupos totales y grupos enmascarados."""
    total, enmascarados = sumar_visibles(filas)
    return {'hora': hora, 'n_viajes': total, 'grupos': len(filas), 'grupos_enmascarados': enmascarados}


def meses_del_anio(anio: int) -> list[Ventana]:
    """[desde, hasta) de cada mes, de diciembre a enero (ninguno pasa de 31 días, el máximo por consulta)."""
    meses = []
    for mes in range(12, 0, -1):
        desde = datetime(anio, mes, 1)
        hasta = datetime(anio + 1, 1, 1) if mes == 12 else datetime(anio, mes + 1, 1)
        meses.append((desde, hasta))
    return meses


# --- cliente -----------------------------------------------------------------------------------------------

class ClienteAcceso:
    """Peticiones a la API de acceso con la clave del portal. Usa el `httpx.AsyncClient` compartido del BFF."""

    def __init__(self, http: httpx.AsyncClient, url: str, clave: str):
        self.http = http
        self.url = url.rstrip('/')
        self.clave = clave

    async def _enviar(self, metodo: str, ruta: str, **kwargs: Any) -> httpx.Response:
        try:
            return await self.http.request(metodo, f'{self.url}{ruta}', headers={'X-API-Key': self.clave},
                                           timeout=TIEMPO_CONSULTA, **kwargs)
        except httpx.HTTPError as error:
            raise ServicioNoDisponible('API de acceso', f'no responde ({type(error).__name__})') from error

    @staticmethod
    def _json(respuesta: httpx.Response) -> Any:
        try:
            return respuesta.json()
        except ValueError as error:
            raise ServicioNoDisponible('API de acceso',
                                       f'respuesta no válida (HTTP {respuesta.status_code})') from error

    @staticmethod
    def _inesperada(respuesta: httpx.Response) -> ServicioNoDisponible:
        if respuesta.status_code == 401:
            return ServicioNoDisponible('API de acceso', 'no acepta la clave del portal (revisa ACCESO_CLAVE)')
        return ServicioNoDisponible('API de acceso', f'ha respondido HTTP {respuesta.status_code}')

    async def _get_json(self, ruta: str, params: dict | None = None) -> Any:
        respuesta = await self._enviar('GET', ruta, params=params)
        if respuesta.status_code != 200:
            raise self._inesperada(respuesta)
        return self._json(respuesta)

    async def catalogo(self) -> dict:
        """`GET /catalogo`, cacheado 10 minutos."""
        clave = (self.url, 'catalogo')
        catalogo = CACHE_CATALOGO.obtener(clave)
        if catalogo is SIN_VALOR:
            catalogo = CACHE_CATALOGO.guardar(clave, await self._get_json('/catalogo'))
        return catalogo

    async def zonas(self, texto: str | None) -> list[dict]:
        """`GET /zonas?texto=`, cacheado 10 minutos por texto (la API busca sin distinguir mayúsculas)."""
        texto = (texto or '').strip()[:50]
        clave = (self.url, 'zonas', texto.lower())
        zonas = CACHE_CATALOGO.obtener(clave)
        if zonas is SIN_VALOR:
            zonas = CACHE_CATALOGO.guardar(clave, await self._get_json('/zonas', {'texto': texto} if texto else None))
        return zonas

    async def consultar(self, consulta: dict) -> tuple[int, Any]:
        """`POST /consultas`: (código, cuerpo) tal cual para 200, 403 y 422. Cualquier otra cosa es un fallo."""
        respuesta = await self._enviar('POST', '/consultas', json=consulta)
        if respuesta.status_code in (200, 403, 422):
            return respuesta.status_code, self._json(respuesta)
        raise self._inesperada(respuesta)

    async def agregados(self, consulta: dict) -> dict:
        """Una consulta interna del BFF que tiene que salir bien: la `Respuesta` (200) o una excepción."""
        codigo, cuerpo = await self.consultar(consulta)
        if codigo == 200:
            return cuerpo
        if codigo == 403:
            raise ConsultaRechazada(cuerpo)
        raise ServicioNoDisponible('API de acceso', 'no ha aceptado una consulta interna del portal (HTTP 422)')

    async def viajes_por_dia_barrio(self, fuente: str, desde: datetime, hasta: datetime) -> list[dict]:
        """Filas `dia_barrio` de [desde, hasta), troceando en ventanas de 31 días si hace falta."""
        filas: list[dict] = []
        for inicio, fin in trocear(desde, hasta):
            respuesta = await self.agregados({'nivel': 'dia_barrio', 'fuente': fuente,
                                              'desde': iso(inicio), 'hasta': iso(fin)})
            filas.extend(respuesta['filas'])
        return filas

    async def viajes_hora_zona(self, fuente: str, desde: datetime, hasta: datetime) -> tuple[list[dict], bool]:
        """Filas `hora_zona` de [desde, hasta) y si alguna ventana vino truncada (500 filas, las primeras horas)."""
        filas: list[dict] = []
        truncada = False
        for inicio, fin in trocear(desde, hasta):
            respuesta = await self.agregados({'nivel': 'hora_zona', 'fuente': fuente,
                                              'desde': iso(inicio), 'hasta': iso(fin)})
            filas.extend(respuesta['filas'])
            truncada = truncada or bool(respuesta.get('truncada'))
        return filas, truncada

    async def dia_barrio_del_mes(self, fuente: str, desde: datetime, hasta: datetime) -> list[dict]:
        """Las filas `dia_barrio` de un mes entero, cacheadas un minuto (también si el mes está vacío)."""
        clave = (self.url, fuente, desde.year, desde.month)
        filas = CACHE_MESES.obtener(clave)
        if filas is SIN_VALOR:
            filas = CACHE_MESES.guardar(clave, await self.viajes_por_dia_barrio(fuente, desde, hasta))
        return filas

    async def dias_con_datos(self, fuente: str, anio: int = ANIO_DATOS) -> AsyncIterator[tuple[datetime, list[dict]]]:
        """Los días con agregados publicados, del último al primero, con sus filas `dia_barrio`.

        Empieza por diciembre y retrocede mes a mes: cada mes es una consulta normal (cacheada) a la API.
        """
        for desde, hasta in meses_del_anio(anio):
            filas = await self.dia_barrio_del_mes(fuente, desde, hasta)
            for dia, filas_dia in reversed(agrupar(filas, 'dia').items()):
                momento = fecha(dia)
                if momento is not None:
                    yield momento, filas_dia

    async def ultimo_dia(self, fuente: str) -> dict | None:
        """`UltimoDia` de la fuente (solo grupos visibles) o None si no hay nada publicado."""
        async for dia, filas in self.dias_con_datos(fuente):
            return resumir_dia(iso(dia), filas)
        return None

    async def ultimas_horas(self, fuente: str, n: int) -> list[tuple[str, list[dict]]]:
        """Las últimas `n` horas con datos de `hora_zona`: [(hora, filas)] en orden ascendente.

        Se recorren los días con datos de atrás hacia delante. Un día con todas las zonas supera las 500 filas y la
        API lo trunca (se quedan las primeras horas), así que en ese caso se pide hora a hora desde el final.
        """
        horas: dict[str, list[dict]] = {}
        dias = 0
        async for dia, _ in self.dias_con_datos(fuente):
            dias += 1
            filas, truncada = await self.viajes_hora_zona(fuente, dia, dia + timedelta(days=1))
            if truncada:
                for h in range(HORAS_DEL_DIA - 1, -1, -1):
                    inicio = dia + timedelta(hours=h)
                    filas_hora, _ = await self.viajes_hora_zona(fuente, inicio, inicio + timedelta(hours=1))
                    if filas_hora:
                        horas[str(filas_hora[0].get('hora'))] = filas_hora
                    if len(horas) >= n:
                        break
            else:
                horas.update(agrupar(filas, 'hora'))
            if len(horas) >= n or dias >= MAX_DIAS_RECORRIDOS:
                break
        return [(hora, horas[hora]) for hora in sorted(horas)[-n:]]


def cliente(cfg: Configuracion, http: httpx.AsyncClient) -> ClienteAcceso:
    return ClienteAcceso(http, cfg.acceso_url, cfg.acceso_clave)
