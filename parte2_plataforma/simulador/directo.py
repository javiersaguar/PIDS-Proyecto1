"""Captura en directo: viajes reales de 2020 enviados a la API de captura en su orden y a su ritmo.

La plataforma recibe los viajes de 2020 como si ocurrieran ahora. Un reloj simulado recorre el mes a `velocidad`
(60 = una hora de 2020 por cada minuto real) y, en cada tic, se envían los viajes cuya recogida ya ha pasado.
Spark los agrega por hora de recogida, así que el tiempo real del portal avanza hora a hora mientras dura.

Datos: `make captura-preparar` descarga un mes de la TLC (por defecto diciembre de 2020: 1,46 millones de viajes)
y lo parte en un CSV comprimido por día en `data/directo/` (`AAAA-MM-DD.csv.gz`), ordenado por recogida y con
las fechas en el formato de la TLC, que es el que acepta la validación. Preparar necesita pyarrow (grupo `datos`);
reproducir solo la biblioteca estándar y httpx, porque lo usan tanto el portal (botón «Capturar datos» del grafo)
como la línea de comandos:

    uv run python -m parte2_plataforma.simulador.directo preparar --mes 2020-12
    uv run python -m parte2_plataforma.simulador.directo portal --velocidad 60     # la arranca el portal
    uv run python -m parte2_plataforma.simulador.directo portal --parar

Un solo emisor: `portal` pide la captura al portal (la misma que el botón), que recuerda por dónde va. `enviar`
reproduce desde este proceso, sin portal; no hay que usarlo a la vez que el portal ni justo después de él, porque
solo sabe por dónde seguir mirando lo que Spark ya ha publicado y repetiría lo que aún no ha agregado.

Orden obligatorio: el trabajo de tiempo real descarta los viajes que llegan más de 2 h por detrás del más reciente
que ha visto (su watermark). Por eso la captura sigue donde se quedó (la última hora publicada en `tr_*`) y nunca
vuelve atrás. Para empezar otra vez por el primer día: `make tiempo-real-reiniciar`.

E3: los viajes pasan por aquí camino de la API de captura, como los de cualquier proveedor; no se guardan ni se
registran, solo se cuentan.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import gzip
import os
import sys
import time
from collections import deque
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / 'data' / 'directo'
COLUMNA_RECOGIDA = 'tpep_pickup_datetime'
FORMATO_TLC = '%m/%d/%Y %I:%M:%S %p'          # config/esquema_viaje.json: formatos_fecha_python
VELOCIDAD_POR_DEFECTO = 60.0                   # una hora de 2020 por minuto real
VELOCIDAD_MAXIMA = 600.0                       # diez horas por minuto: unos 500 viajes/s en hora punta
TIC_S = 1.0                                    # cada cuánto avanza el reloj y se envía
MAX_LOTE = 1000                                # MAX_VIAJES_POR_LOTE de la API de captura
VENTANA_RITMO_S = 10.0                         # ritmo medio de envío de los últimos segundos
TIEMPO_PETICION = 30.0


class SinDatos(Exception):
    """No hay ficheros preparados, o ya se ha enviado todo lo que hay a partir del punto pedido."""


class ErrorCaptura(Exception):
    """La API de captura ha rechazado un lote."""


# --- preparación (una vez, en el anfitrión) ------------------------------------------------------------------

def preparar(parquet: Path, destino: Path = CARPETA, mes: str | None = None) -> dict[str, int]:
    """Parte el Parquet mensual de la TLC en un CSV.gz por día, ordenado por recogida. Devuelve viajes por día.

    Se quedan fuera los viajes con la recogida fuera del mes (el fichero de la TLC trae algunos de 2003 o de 2021).
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    tabla = pq.read_table(parquet)
    recogida = tabla[COLUMNA_RECOGIDA]
    if mes:
        inicio = datetime.strptime(mes, '%Y-%m')
        fin = (inicio + timedelta(days=32)).replace(day=1)
        tabla = tabla.filter(pc.and_(pc.greater_equal(recogida, inicio), pc.less(recogida, fin)))
    tabla = tabla.sort_by(COLUMNA_RECOGIDA)
    dias = pc.strftime(tabla[COLUMNA_RECOGIDA], format='%Y-%m-%d').to_pylist()
    columnas = [c for c in tabla.column_names if c != 'airport_fee']   # 2020 no la tenía: va vacía
    valores = {c: tabla[c].to_pylist() for c in columnas}
    destino.mkdir(parents=True, exist_ok=True)
    cuentas: dict[str, int] = {}
    escritor, fichero, dia_actual = None, None, None
    try:
        for i, dia in enumerate(dias):
            if dia != dia_actual:
                if fichero:
                    fichero.close()
                fichero = gzip.open(destino / f'{dia}.csv.gz', 'wt', newline='', encoding='utf-8')
                escritor = csv.writer(fichero)
                escritor.writerow(columnas)
                dia_actual, cuentas[dia] = dia, 0
            escritor.writerow([_texto(valores[c][i]) for c in columnas])
            cuentas[dia] += 1
    finally:
        if fichero:
            fichero.close()
    return cuentas


def _texto(valor) -> str:
    if valor is None:
        return ''
    if isinstance(valor, datetime):
        return valor.strftime(FORMATO_TLC)
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


# --- lectura ------------------------------------------------------------------------------------------------

def dias_disponibles(carpeta: Path = CARPETA) -> list[date]:
    if not carpeta.is_dir():
        return []
    dias = []
    for ruta in carpeta.glob('*.csv.gz'):
        try:
            dias.append(date.fromisoformat(ruta.name.removesuffix('.csv.gz')))
        except ValueError:
            continue
    return sorted(dias)


def recogida(viaje: dict) -> datetime:
    return datetime.strptime(viaje[COLUMNA_RECOGIDA], FORMATO_TLC)


def viajes_desde(carpeta: Path, desde: datetime) -> Iterator[dict]:
    """Los viajes preparados con recogida >= `desde`, en orden, leyendo un día cada vez (memoria constante)."""
    for dia in dias_disponibles(carpeta):
        if dia < desde.date():
            continue
        with gzip.open(carpeta / f'{dia}.csv.gz', 'rt', newline='', encoding='utf-8') as fichero:
            for fila in csv.DictReader(fichero):
                viaje = {clave: (valor if valor != '' else None) for clave, valor in fila.items()}
                if recogida(viaje) >= desde:
                    yield viaje


def punto_de_partida(dias: list[date], ultima_hora: datetime | None, reloj: datetime | None = None) -> datetime:
    """Dónde sigue la captura: el reloj de la anterior (mismo proceso) o la hora siguiente a la última publicada.

    Sin nada publicado, el primer día a las 00:00. Lanza `SinDatos` si no queda nada por enviar desde ahí.
    """
    if not dias:
        raise SinDatos('No hay viajes preparados en data/directo: ejecuta `make captura-preparar`')
    primero = datetime.combine(dias[0], datetime.min.time())
    fin = datetime.combine(dias[-1], datetime.min.time()) + timedelta(days=1)
    publicada = ultima_hora.replace(minute=0, second=0, microsecond=0) if ultima_hora is not None else None
    desde = primero
    if publicada is not None:
        desde = max(desde, publicada + timedelta(hours=1))
    if reloj is not None and (publicada is None or reloj >= publicada):
        desde = max(primero, reloj)       # la hora a medias es nuestra: se sigue en el minuto exacto
    if desde >= fin:
        raise SinDatos(f'Ya se ha capturado todo hasta el {fin - timedelta(days=1):%d/%m/%Y}: para volver a empezar, '
                       '`make tiempo-real-reiniciar`')
    return desde


# --- reproducción -------------------------------------------------------------------------------------------

@dataclass
class Progreso:
    """Lo que la reproducción va contando. El portal lo copia a su `EstadoSimulacion`."""
    enviados: int = 0
    reloj: datetime | None = None
    ritmo: float = 0.0          # viajes por segundo real, media de los últimos VENTANA_RITMO_S


Enviar = Callable[[list[dict]], Awaitable[None]]


async def reproducir(enviar: Enviar, carpeta: Path, desde: datetime, velocidad: float,
                     progreso: Progreso | None = None, tic: float = TIC_S,
                     reloj_real: Callable[[], float] = time.monotonic) -> Progreso:
    """Envía los viajes a medida que el reloj simulado los alcanza. Termina al acabarse los datos (o al cancelarla)."""
    progreso = progreso or Progreso()
    velocidad = max(1.0, min(float(velocidad), VELOCIDAD_MAXIMA))
    viajes = viajes_desde(carpeta, desde)
    pendiente = next(viajes, None)
    if pendiente is None:
        raise SinDatos(f'No hay viajes preparados a partir del {desde:%d/%m/%Y %H:%M}')
    inicio = reloj_real()
    historial: deque[tuple[float, int]] = deque()
    while pendiente is not None:
        ahora = reloj_real()
        reloj = desde + timedelta(seconds=(ahora - inicio) * velocidad)
        lote: list[dict] = []
        while pendiente is not None and recogida(pendiente) <= reloj:
            lote.append(pendiente)
            pendiente = next(viajes, None)
            if len(lote) == MAX_LOTE:
                await enviar(lote)
                progreso.enviados += len(lote)
                lote = []
        if lote:
            await enviar(lote)
            progreso.enviados += len(lote)
        progreso.reloj = reloj
        historial.append((ahora, progreso.enviados))
        while historial and ahora - historial[0][0] > VENTANA_RITMO_S:
            historial.popleft()
        if len(historial) > 1 and historial[-1][0] > historial[0][0]:
            progreso.ritmo = (historial[-1][1] - historial[0][1]) / (historial[-1][0] - historial[0][0])
        if pendiente is not None:
            await asyncio.sleep(tic)
    return progreso


def enviador(http: httpx.AsyncClient, url_captura: str, clave: str, lote: str) -> Enviar:
    """`enviar(viajes)` contra `POST {url}/viajes` con la clave del simulador."""
    async def enviar(viajes: list[dict]) -> None:
        respuesta = await http.post(f'{url_captura.rstrip("/")}/viajes', json={'lote': lote, 'viajes': viajes},
                                    headers={'X-API-Key': clave}, timeout=TIEMPO_PETICION)
        if respuesta.status_code >= 400:
            raise ErrorCaptura(f'La API de captura ha respondido HTTP {respuesta.status_code}')
    return enviar


def nombre_lote(ahora: datetime | None = None) -> str:
    return f'directo-{(ahora or datetime.now()):%Y%m%d%H%M%S}'


# --- la última hora publicada, por la API de acceso ------------------------------------------------------------

Consultar = Callable[[dict], Awaitable[list[dict]]]


async def ultima_hora_publicada(consultar: Consultar, dias: list[date]) -> datetime | None:
    """La última hora con agregados de tiempo real dentro de los días preparados, o None si no hay ninguna.

    Solo consultas normales a la API de acceso (quedan en la auditoría): día y barrio hacia atrás hasta encontrar un
    día con datos, y después ese día hora a hora desde el final.
    """
    for dia in sorted(dias, reverse=True):
        inicio = datetime.combine(dia, datetime.min.time())
        filas = await consultar({'nivel': 'dia_barrio', 'fuente': 'tiempo_real',
                                 'desde': f'{inicio:%Y-%m-%dT%H:%M:%S}',
                                 'hasta': f'{inicio + timedelta(days=1):%Y-%m-%dT%H:%M:%S}'})
        if not filas:
            continue
        for hora in range(23, -1, -1):
            momento = inicio + timedelta(hours=hora)
            filas = await consultar({'nivel': 'hora_zona', 'fuente': 'tiempo_real',
                                     'desde': f'{momento:%Y-%m-%dT%H:%M:%S}',
                                     'hasta': f'{momento + timedelta(hours=1):%Y-%m-%dT%H:%M:%S}'})
            if filas:
                return momento
        return inicio
    return None


def consultor(http: httpx.AsyncClient, url_acceso: str, clave: str) -> Consultar:
    async def consultar(consulta: dict) -> list[dict]:
        respuesta = await http.post(f'{url_acceso.rstrip("/")}/consultas', json=consulta,
                                    headers={'X-API-Key': clave}, timeout=TIEMPO_PETICION)
        respuesta.raise_for_status()
        return respuesta.json()['filas']
    return consultar


# --- línea de comandos --------------------------------------------------------------------------------------------

def _entorno() -> dict[str, str]:
    valores = {}
    ruta = RAIZ / '.env'
    if ruta.is_file():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            if '=' in linea and not linea.lstrip().startswith('#'):
                clave, valor = linea.split('=', 1)
                valores[clave.strip()] = valor.strip().strip('"\'')
    return {**valores, **os.environ}


async def _enviar_cli(args: argparse.Namespace) -> int:
    cfg = _entorno()
    dias = dias_disponibles(args.carpeta)
    async with httpx.AsyncClient() as http:
        consultar = consultor(http, f'http://127.0.0.1:{cfg.get("PUERTO_ACCESO", "8002")}', cfg['ACCESO_CLAVE_EQUIPO'])
        desde = (datetime.fromisoformat(args.desde) if args.desde
                 else punto_de_partida(dias, await ultima_hora_publicada(consultar, dias)))
        lote = nombre_lote()
        enviar = enviador(http, f'http://127.0.0.1:{cfg.get("PUERTO_CAPTURA", "8001")}',
                          cfg['CAPTURA_CLAVE_SIMULADOR'], lote)
        progreso = Progreso()
        print(f'Captura en directo {lote}: desde el {desde:%d/%m/%Y %H:%M} de 2020 a ×{args.velocidad:g} '
              f'(Ctrl+C para parar)', flush=True)
        tarea = asyncio.create_task(reproducir(enviar, args.carpeta, desde, args.velocidad, progreso))
        limite = time.monotonic() + args.durante if args.durante else None
        try:
            while not tarea.done():
                await asyncio.sleep(2)
                if limite and time.monotonic() >= limite:
                    tarea.cancel()
                    break
                if progreso.reloj:
                    print(f'\r  reloj {progreso.reloj:%d/%m/%Y %H:%M} · {progreso.enviados:,} viajes · '
                          f'{progreso.ritmo:,.0f} viajes/s   ', end='', flush=True)
            await tarea
        except (KeyboardInterrupt, asyncio.CancelledError):
            tarea.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tarea
        print(f'\n{progreso.enviados:,} viajes enviados · reloj en {progreso.reloj:%d/%m/%Y %H:%M}')
    return 0


def _portal_cli(args: argparse.Namespace) -> int:
    """Arranca o para la captura en el portal (`POST`/`DELETE /api/operaciones/captura`), con su contraseña."""
    cfg = _entorno()
    url = f'http://127.0.0.1:{cfg.get("PUERTO_FRONTEND", "8020")}'
    with httpx.Client(base_url=url, timeout=TIEMPO_PETICION) as http:
        try:
            r = http.post('/api/sesion', json={'clave': cfg['FRONTEND_CLAVE']})
        except httpx.HTTPError:
            print(f'El portal no responde en {url}: levántalo con `make frontend`', file=sys.stderr)
            return 1
        if r.status_code != 204:
            print(f'El portal no acepta la contraseña de .env (HTTP {r.status_code})', file=sys.stderr)
            return 1
        if args.parar:
            estado = http.delete('/api/operaciones/captura').json()
            print(f'Captura parada: {estado["enviados"]:,} viajes enviados · reloj en {estado.get("reloj")}')
            return 0
        r = http.post('/api/operaciones/captura', json={'velocidad': args.velocidad})
        if r.status_code != 202:
            print(r.json().get('detail', f'HTTP {r.status_code}'), file=sys.stderr)
            return 1
        estado = r.json()
        print(f'Capturando desde el {datetime.fromisoformat(estado["reloj"]):%d/%m/%Y %H:%M} de 2020 a ×{args.velocidad:g} '
              f'({estado["lote"]}). Se ve en el portal: Grafo y Tiempo real. Para pararla: make capturar-parar')
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='orden', required=True)
    pp = sub.add_parser('preparar', help='parte un Parquet mensual de la TLC en un CSV.gz por día')
    pp.add_argument('--mes', default='2020-12')
    pp.add_argument('--parquet', type=Path, help='por defecto data/crudo/yellow_tripdata_<mes>.parquet')
    pp.add_argument('--carpeta', type=Path, default=CARPETA)
    pp2 = sub.add_parser('portal', help='arranca (o para, con --parar) la captura en el portal')
    pp2.add_argument('--velocidad', type=float, default=VELOCIDAD_POR_DEFECTO)
    pp2.add_argument('--parar', action='store_true')
    pe = sub.add_parser('enviar', help='reproduce desde este proceso contra la API de captura, sin portal')
    pe.add_argument('--velocidad', type=float, default=VELOCIDAD_POR_DEFECTO,
                    help=f'segundos de 2020 por segundo real (1-{VELOCIDAD_MAXIMA:g}; 60 = una hora por minuto)')
    pe.add_argument('--desde', help='AAAA-MM-DDTHH:MM (por defecto, la hora siguiente a la última publicada)')
    pe.add_argument('--durante', type=float, help='parar al cabo de estos segundos (por defecto, hasta Ctrl+C)')
    pe.add_argument('--carpeta', type=Path, default=CARPETA)
    args = p.parse_args()
    try:
        if args.orden == 'preparar':
            parquet = args.parquet or RAIZ / 'data' / 'crudo' / f'yellow_tripdata_{args.mes}.parquet'
            if not parquet.is_file():
                print(f'Falta {parquet}: descárgalo con `make descargar MES={args.mes}`', file=sys.stderr)
                return 2
            cuentas = preparar(parquet, args.carpeta, args.mes)
            print(f'{sum(cuentas.values()):,} viajes en {len(cuentas)} días → {args.carpeta}')
            return 0
        if args.orden == 'portal':
            return _portal_cli(args)
        return asyncio.run(_enviar_cli(args))
    except SinDatos as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
