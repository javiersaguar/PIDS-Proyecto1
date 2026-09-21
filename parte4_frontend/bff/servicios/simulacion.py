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
"""
from __future__ import annotations

import asyncio
import csv
import logging
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

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


def nombre_lote(fichero: str, ahora: datetime) -> str:
    """`portal-<fichero sin extensión>-<AAAAMMDDHHMMSS>`, recortado a los 100 caracteres que admite la captura."""
    sufijo = f'-{ahora:%Y%m%d%H%M%S}'
    return f'portal-{Path(fichero).stem}'[:MAX_LARGO_LOTE - len(sufijo)] + sufijo


def espera_para_ritmo(enviados: int, ritmo: float, transcurrido: float) -> float:
    """Segundos que faltan para no pasar de `ritmo` viajes/s tras haber enviado `enviados` en `transcurrido` s."""
    return max(0.0, enviados / ritmo - transcurrido)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass
class EstadoSimulacion:
    """`Simulacion` del contrato (más `fin`, el instante en que terminó o se detuvo)."""
    activa: bool = False
    lote: str | None = None
    fichero: str | None = None
    enviados: int = 0
    total: int = 0
    ritmo: float = RITMO_POR_DEFECTO
    inicio: str | None = None
    fin: str | None = None
    error: str | None = None

    def a_dict(self) -> dict:
        return asdict(self)


# --- simulador ---------------------------------------------------------------------------------------------

class Simulador:
    """Una simulación como mucho por proceso; el estado se conserva hasta que empieza la siguiente."""

    def __init__(self, carpeta: Path = CARPETA_MUESTRA):
        self.carpeta = carpeta
        self.estado = EstadoSimulacion()
        self._tarea: asyncio.Task | None = None

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
                      ritmo: float = RITMO_POR_DEFECTO, maximo: int | None = None) -> dict:
        if self.activa:
            raise SimulacionActiva('Ya hay una simulación en marcha')
        ruta = self.ruta(fichero)
        viajes = await asyncio.to_thread(leer_viajes, ruta, maximo)
        if not viajes:
            raise FicheroNoPermitido(f'El fichero {fichero!r} no tiene viajes')
        ahora = datetime.now()
        self.estado = EstadoSimulacion(activa=True, lote=nombre_lote(fichero, ahora), fichero=fichero,
                                       total=len(viajes), ritmo=ritmo, inicio=_ahora())
        self._tarea = asyncio.create_task(self._enviar(http, url.rstrip('/'), clave, viajes))
        log.info('Simulación %s iniciada: %d viajes de %s a %.0f viajes/s',
                 self.estado.lote, len(viajes), fichero, ritmo)
        return self.estado.a_dict()

    async def parar(self) -> dict:
        if self._tarea is not None and not self._tarea.done():
            self._tarea.cancel()
            with suppress(asyncio.CancelledError):
                await self._tarea
        return self.estado.a_dict()

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
