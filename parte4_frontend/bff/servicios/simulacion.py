"""Simulador de tiempo real integrado en el portal: reenvía los viajes de un CSV de `data/muestra` a la API de
captura como si llegaran en directo. Reimplementación de `parte2_plataforma/simulador/simulador.py` con la
biblioteca estándar (`csv`, `datetime`) y `httpx`: pandas no va en la imagen del portal.

- Solo se admiten ficheros de `data/muestra` (la carpeta que la imagen copia); cualquier otra ruta se rechaza
  (`FicheroNoPermitido` -> 400). `ficheros()` lista los que hay.
- Los viajes se ordenan por `tpep_pickup_datetime` (formato `%m/%d/%Y %I:%M:%S %p`) porque el procesado en tiempo
  real usa la hora del viaje; las filas cuya fecha no se entiende van al final, en su orden original.
- Lotes de 100 viajes a `POST {CAPTURA_URL}/viajes` con `X-API-Key` y `{"lote": "portal-<fichero>-<fecha>",
  "viajes": [...]}`, al ritmo pedido (viajes por segundo), en una `asyncio.Task` en segundo plano.
- Una sola simulación activa por proceso (`SimulacionActiva` -> 409); `parar()` cancela la tarea.
- Los valores del CSV se envían como texto tal cual (celda vacía -> null): la API de captura no valida y Spark
  normaliza. E3: aquí no se guarda ni se registra ningún viaje, solo se cuentan.
- `sinteticos=N` no envía el fichero: lo usa de plantilla para inventar N viajes
  (`parte2_plataforma/simulador/sinteticos.py`), porque la muestra tiene 999 y se agota en segundos. Cumplen las
  mismas reglas de `config/esquema_viaje.json`, así que la plataforma los da por válidos, y se fechan a partir de
  la última hora publicada en tiempo real: con una fecha anterior, la marca de agua de Spark los descartaría.

Captura en directo (`iniciar_directo`, botón «Capturar datos» del grafo): viajes reales de un mes de 2020 que se
envían con un reloj simulado, sin fin fijo (`parte2_plataforma/simulador/directo.py`). Comparte el estado con la
simulación de ficheros (`modo: 'directo'`, `reloj`, `velocidad`), así que las animaciones del grafo y la página de
Operaciones la ven igual, y sigue siendo una sola a la vez.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from parte2_plataforma.simulador import directo as DIRECTO
from parte2_plataforma.simulador import sinteticos as SINTETICOS

from ..configuracion import RAIZ

log = logging.getLogger('pids.frontend')

CARPETA_MUESTRA = RAIZ / 'data' / 'muestra'
COLUMNA_RECOGIDA = 'tpep_pickup_datetime'
FORMATOS_FECHA = ('%m/%d/%Y %I:%M:%S %p',        # TLC (yellow_tripdata_2020_muestra.csv)
                  '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                  '%Y %b %d %I:%M:%S %p')        # exportacion_formato_europeo.csv
TAMANO_LOTE = 100
RITMO_POR_DEFECTO = 50.0                       # viajes por segundo
TIEMPO_CAPTURA = 30.0                          # segundos por petición
MAX_LARGO_LOTE = 100                           # `lote` en la API de captura: max_length=100
FECHA_MAXIMA = datetime.max                    # clave de orden de las fechas ilegibles: al final


MAXIMO_SINTETICOS = 200_000                    # tope del portal: generar más bloquearía la petición


class FicheroNoPermitido(Exception):
    """El fichero no está en `data/muestra` o no es un CSV legible."""


class SimulacionActiva(Exception):
    """Ya hay una simulación en marcha en este proceso."""


class ErrorCaptura(Exception):
    """La API de captura ha respondido con error a un lote."""


# --- lógica pura -------------------------------------------------------------------------------------------

def fecha_recogida(texto: str | None) -> datetime:
    """La fecha de recogida en cualquiera de los formatos conocidos; si no se entiende, la máxima (va al final)."""
    if texto:
        for formato in FORMATOS_FECHA:
            try:
                return datetime.strptime(texto.strip(), formato)
            except ValueError:
                continue
    return FECHA_MAXIMA


def leer_viajes(ruta: Path, maximo: int | None = None) -> list[dict]:
    """Las filas del CSV como diccionarios de texto (vacío -> None), ordenadas por recogida (orden estable)."""
    with ruta.open(newline='', encoding='utf-8-sig') as fichero:
        lector = csv.DictReader(fichero)
        filas = [{clave: (valor if valor != '' else None) for clave, valor in fila.items() if clave is not None}
                 for fila in lector]
    columna = next((c for c in (lector.fieldnames or []) if c.lower() == COLUMNA_RECOGIDA), None)
    if columna is not None:
        filas.sort(key=lambda fila: fecha_recogida(fila.get(columna)))
    return filas[:maximo] if maximo else filas


def lotes(viajes: list[dict], tamano: int = TAMANO_LOTE) -> Iterator[list[dict]]:
    for inicio in range(0, len(viajes), tamano):
        yield viajes[inicio:inicio + tamano]


def nombre_lote(fichero: str, ahora: datetime, sinteticos: int | None = None) -> str:
    """`portal-<fichero sin extensión>-<AAAAMMDDHHMMSS>`, recortado a los 100 caracteres que admite la captura.

    Con viajes generados, `portal-sinteticos-<N>-…`: así se distinguen en la auditoría y en los lotes de S3.
    """
    sufijo = f'-{ahora:%Y%m%d%H%M%S}'
    cuerpo = f'portal-sinteticos-{sinteticos}' if sinteticos else f'portal-{Path(fichero).stem}'
    return cuerpo[:MAX_LARGO_LOTE - len(sufijo)] + sufijo


def espera_para_ritmo(enviados: int, ritmo: float, transcurrido: float) -> float:
    """Segundos que faltan para no pasar de `ritmo` viajes/s tras haber enviado `enviados` en `transcurrido` s."""
    return max(0.0, enviados / ritmo - transcurrido)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass
class EstadoSimulacion:
    """`Simulacion` del contrato (más `fin`, el instante en que terminó o se detuvo).

    En la captura en directo: `modo='directo'`, `total=0` (no tiene fin fijo), `ritmo` es el ritmo real medido
    (viajes/s), `reloj` la hora de 2020 por la que va y `velocidad` cuántos segundos de 2020 pasan por segundo.
    """
    activa: bool = False
    lote: str | None = None
    fichero: str | None = None
    sinteticos: int | None = None                  # viajes generados a partir del fichero, si no se envía tal cual
    enviados: int = 0
    total: int = 0
    ritmo: float = RITMO_POR_DEFECTO
    inicio: str | None = None
    fin: str | None = None
    error: str | None = None
    modo: str = 'fichero'
    reloj: str | None = None
    velocidad: float | None = None

    def a_dict(self) -> dict:
        return asdict(self)


# --- simulador ---------------------------------------------------------------------------------------------

class Simulador:
    """Una simulación como mucho por proceso; el estado se conserva hasta que empieza la siguiente."""

    def __init__(self, carpeta: Path = CARPETA_MUESTRA, carpeta_directo: Path = DIRECTO.CARPETA):
        self.carpeta = carpeta
        self.carpeta_directo = carpeta_directo
        self.estado = EstadoSimulacion()
        self._tarea: asyncio.Task | None = None
        self._progreso: DIRECTO.Progreso | None = None
        self.reloj_directo: datetime | None = None        # por dónde iba la última captura en directo

    def estado_actual(self) -> dict:
        """El estado, con el progreso de la captura en directo al día."""
        if self._progreso is not None:
            self.estado.enviados = self._progreso.enviados
            self.estado.ritmo = round(self._progreso.ritmo, 1)
            if self._progreso.reloj is not None:
                self.estado.reloj = self._progreso.reloj.isoformat(timespec='seconds')
                self.reloj_directo = self._progreso.reloj
        return self.estado.a_dict()

    def info_directo(self) -> dict:
        """Qué hay preparado para la captura en directo y por dónde seguiría."""
        dias = DIRECTO.dias_disponibles(self.carpeta_directo)
        return {
            'disponible': bool(dias),
            'primer_dia': dias[0].isoformat() if dias else None,
            'ultimo_dia': dias[-1].isoformat() if dias else None,
            'reloj': self.reloj_directo.isoformat(timespec='seconds') if self.reloj_directo else None,
            'velocidad_por_defecto': DIRECTO.VELOCIDAD_POR_DEFECTO,
            'velocidad_maxima': DIRECTO.VELOCIDAD_MAXIMA,
        }

    async def iniciar_directo(self, http: httpx.AsyncClient, url: str, clave: str, consultar: DIRECTO.Consultar,
                              velocidad: float = DIRECTO.VELOCIDAD_POR_DEFECTO, desde: datetime | None = None) -> dict:
        """Arranca la captura en directo donde se quedó (`DIRECTO.punto_de_partida`). `SinDatos` si no hay nada."""
        if self.activa:
            raise SimulacionActiva('Ya hay una simulación en marcha')
        dias = DIRECTO.dias_disponibles(self.carpeta_directo)
        if desde is None:
            ultima = await DIRECTO.ultima_hora_publicada(consultar, dias) if dias else None
            desde = DIRECTO.punto_de_partida(dias, ultima, self.reloj_directo)
        self._progreso = DIRECTO.Progreso(reloj=desde)
        self.estado = EstadoSimulacion(activa=True, lote=DIRECTO.nombre_lote(), total=0, ritmo=0.0, inicio=_ahora(),
                                       modo='directo', reloj=desde.isoformat(timespec='seconds'), velocidad=velocidad)
        enviar = DIRECTO.enviador(http, url, clave, self.estado.lote)
        self._tarea = asyncio.create_task(self._directo(enviar, desde, velocidad))
        log.info('Captura en directo %s desde %s a ×%g', self.estado.lote, desde, velocidad)
        return self.estado_actual()

    async def _directo(self, enviar: DIRECTO.Enviar, desde: datetime, velocidad: float) -> None:
        estado, progreso = self.estado, self._progreso
        try:
            await DIRECTO.reproducir(enviar, self.carpeta_directo, desde, velocidad, progreso)
            log.info('Captura en directo %s: fin de los datos preparados (%d viajes)', estado.lote, progreso.enviados)
        except asyncio.CancelledError:
            log.info('Captura en directo %s detenida con %d viajes enviados', estado.lote, progreso.enviados)
            raise
        except httpx.HTTPError as error:
            estado.error = f'La API de captura no responde ({type(error).__name__})'
        except (DIRECTO.ErrorCaptura, DIRECTO.SinDatos) as error:
            estado.error = str(error)
        finally:
            self.estado_actual()
            estado.activa = False
            estado.fin = _ahora()
            if estado.error:
                log.warning('Captura en directo %s interrumpida: %s', estado.lote, estado.error)

    def ficheros(self) -> list[str]:
        if not self.carpeta.is_dir():
            return []
        return sorted(p.name for p in self.carpeta.iterdir() if p.is_file() and p.suffix.lower() == '.csv')

    def ruta(self, fichero: str) -> Path:
        """La ruta de un fichero permitido: nombre simple, dentro de la carpeta (resuelta) y un CSV que existe."""
        if not fichero or Path(fichero).name != fichero or fichero.startswith('.'):
            raise FicheroNoPermitido('Solo se admite el nombre de un fichero de data/muestra')
        candidato = (self.carpeta / fichero).resolve()
        if candidato.parent != self.carpeta.resolve() or not candidato.is_file() or candidato.suffix.lower() != '.csv':
            raise FicheroNoPermitido(f'El fichero {fichero!r} no está en data/muestra o no es un CSV')
        return candidato

    @property
    def activa(self) -> bool:
        return self._tarea is not None and not self._tarea.done()

    async def iniciar(self, http: httpx.AsyncClient, url: str, clave: str, fichero: str,
                      ritmo: float = RITMO_POR_DEFECTO, maximo: int | None = None,
                      sinteticos: int | None = None, semilla: int | None = None,
                      consultar: DIRECTO.Consultar | None = None) -> dict:
        if self.activa:
            raise SimulacionActiva('Ya hay una simulación en marcha')
        ruta = self.ruta(fichero)
        if sinteticos:
            desde = await self._desde_para_sinteticos(consultar)
            viajes = await asyncio.to_thread(self._generar, ruta, sinteticos, semilla, desde)
        else:
            viajes = await asyncio.to_thread(leer_viajes, ruta, maximo)
        if not viajes:
            raise FicheroNoPermitido(f'El fichero {fichero!r} no tiene viajes')
        ahora = datetime.now()
        self._progreso = None
        self.estado = EstadoSimulacion(activa=True, lote=nombre_lote(fichero, ahora, sinteticos), fichero=fichero,
                                       sinteticos=sinteticos, total=len(viajes), ritmo=ritmo, inicio=_ahora())
        self._tarea = asyncio.create_task(self._enviar(http, url.rstrip('/'), clave, viajes))
        log.info('Simulación %s iniciada: %d viajes %s %s a %.0f viajes/s', self.estado.lote, len(viajes),
                 'generados a partir de' if sinteticos else 'de', fichero, ritmo)
        return self.estado.a_dict()

    async def _desde_para_sinteticos(self, consultar: DIRECTO.Consultar | None) -> datetime | None:
        """Desde qué hora de 2020 inventar los viajes, para que el streaming no los descarte.

        Spark publica en tiempo real con marca de agua: lo anterior a la última hora publicada se tira. Si
        se sabe por dónde va (la última hora publicada, o el reloj de la última captura en directo), se
        genera a partir de ahí; si no, se usan los días de la plantilla.
        """
        ultima = self.reloj_directo
        dias = DIRECTO.dias_disponibles(self.carpeta_directo)
        if consultar is not None and dias:
            try:
                publicada = await DIRECTO.ultima_hora_publicada(consultar, dias)
            except httpx.HTTPError:                  # la API de acceso no responde: no es motivo para fallar
                publicada = None
            if publicada is not None and (ultima is None or publicada > ultima):
                ultima = publicada
        return ultima.replace(minute=0, second=0, microsecond=0) if ultima else None

    @staticmethod
    def _generar(ruta: Path, cuantos: int, semilla: int | None, desde: datetime | None = None) -> list[dict]:
        """Viajes inventados con la plantilla elegida; los errores se traducen al 400 del contrato."""
        if cuantos > MAXIMO_SINTETICOS:
            raise FicheroNoPermitido(f'Como mucho se pueden generar {MAXIMO_SINTETICOS:,} viajes')
        hasta = min(desde + timedelta(days=1), SINTETICOS.ventana()[1]) if desde else None
        if desde and desde >= hasta:                  # el 31 de diciembre ya no cabe otro día: sin tramo
            desde = hasta = None
        try:
            return SINTETICOS.generar(cuantos, ruta, semilla, desde, hasta)[1]
        except (SINTETICOS.SinPlantillas, ValueError) as error:
            raise FicheroNoPermitido(f'No se han podido generar viajes con {ruta.name!r}: {error}') from error

    async def parar(self) -> dict:
        if self._tarea is not None and not self._tarea.done():
            self._tarea.cancel()
            with suppress(asyncio.CancelledError):
                await self._tarea
        return self.estado_actual()

    async def _enviar(self, http: httpx.AsyncClient, url: str, clave: str, viajes: list[dict]) -> None:
        estado = self.estado
        inicio = time.monotonic()
        try:
            for lote in lotes(viajes):
                respuesta = await http.post(f'{url}/viajes', json={'lote': estado.lote, 'viajes': lote},
                                            headers={'X-API-Key': clave}, timeout=TIEMPO_CAPTURA)
                if respuesta.status_code >= 400:
                    raise ErrorCaptura(f'La API de captura ha respondido HTTP {respuesta.status_code}')
                estado.enviados += len(lote)
                espera = espera_para_ritmo(estado.enviados, estado.ritmo, time.monotonic() - inicio)
                if espera > 0:
                    await asyncio.sleep(espera)
            log.info('Simulación %s completada: %d viajes', estado.lote, estado.enviados)
        except asyncio.CancelledError:
            log.info('Simulación %s detenida con %d de %d viajes enviados', estado.lote, estado.enviados, estado.total)
            raise
        except httpx.HTTPError as error:
            estado.error = f'La API de captura no responde ({type(error).__name__})'
            log.warning('Simulación %s interrumpida: %s', estado.lote, estado.error)
        except ErrorCaptura as error:
            estado.error = str(error)
            log.warning('Simulación %s interrumpida: %s', estado.lote, estado.error)
        finally:
            estado.activa = False
            estado.fin = _ahora()


SIMULADOR = Simulador()
