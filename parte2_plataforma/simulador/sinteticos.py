"""Viajes sintéticos con el formato de la TLC, a partir de una muestra real.

Para las demos: la muestra de Moodle tiene 999 viajes y se agota en segundos. Este generador
produce tantos como haga falta tomando cada fila de la muestra como plantilla y variándola
(día, duración, distancia, importes y, si se pide, zonas).

Las reglas salen de `config/esquema_viaje.json`, el mismo fichero que usan la captura y Spark, así
que todo lo generado pasa la validación: fechas dentro de 2020, duración y distancia dentro de los
máximos, y zonas entre 1 y 265. Los campos con lista de valores (proveedor, tarifa, tipo de pago)
se copian de la plantilla. Solo se usa la biblioteca estándar: la imagen del portal no lleva pandas.

Uso:
    uv run python -m parte2_plataforma.simulador.sinteticos 10000
    uv run python -m parte2_plataforma.simulador.sinteticos 5000 --salida data/muestra/sinteticos.csv \
        --desde 2020-03-01 --hasta 2020-03-08 --semilla 7

Los datos son inventados: no hay ningún viaje real detrás, así que no pueden identificar a nadie.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', RAIZ / 'config'))
PLANTILLA_POR_DEFECTO = RAIZ / 'data' / 'muestra' / 'yellow_tripdata_2020_muestra.csv'

FORMATO_FECHA = '%m/%d/%Y %I:%M:%S %p'          # el de la muestra de Moodle
COLUMNA_RECOGIDA = 'tpep_pickup_datetime'
COLUMNA_LLEGADA = 'tpep_dropoff_datetime'
IMPUESTO_MTA = 0.5
RECARGO_MEJORA = 0.3
DURACION_MINIMA = timedelta(minutes=2)
DURACION_TIPICA = timedelta(minutes=75)         # tope antes de ajustarla por distancia
MAXIMO_FILAS = 5_000_000


class SinPlantillas(Exception):
    """El CSV de plantilla no existe, está vacío o no tiene el esquema de la TLC."""


def reglas() -> dict:
    """Las reglas de `config/esquema_viaje.json` (las mismas que aplican la captura y Spark)."""
    return json.loads((RUTA_CONFIG / 'esquema_viaje.json').read_text(encoding='utf-8'))['reglas']


def ventana(regs: dict | None = None) -> tuple[datetime, datetime]:
    """Instantes entre los que puede caer una recogida válida (`hasta` no se incluye)."""
    regs = regs or reglas()
    return datetime.fromisoformat(regs['recogida_desde']), datetime.fromisoformat(regs['recogida_hasta'])


def leer_plantillas(ruta: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Cabecera y filas del CSV de plantilla, tal cual (texto)."""
    if not ruta.is_file():
        raise SinPlantillas(f'no existe el CSV de plantilla: {ruta}')
    with ruta.open(newline='', encoding='utf-8-sig') as fichero:
        lector = csv.DictReader(fichero)
        columnas = list(lector.fieldnames or [])
        filas = [fila for fila in lector]
    faltan = {COLUMNA_RECOGIDA, COLUMNA_LLEGADA} - {c.lower() for c in columnas}
    if faltan:
        raise SinPlantillas(f'el CSV de plantilla no tiene el esquema de la TLC: faltan {", ".join(sorted(faltan))}')
    if not filas:
        raise SinPlantillas(f'el CSV de plantilla no tiene filas: {ruta}')
    return columnas, filas


def _numero(texto: str | None, por_defecto: float = 0.0) -> float:
    """Un número de la plantilla; acepta coma decimal y devuelve `por_defecto` si está vacío o mal."""
    try:
        return float(str(texto).replace(',', '.'))
    except (TypeError, ValueError):
        return por_defecto


def _dinero(valor: float) -> str:
    return f'{max(0.0, valor):.2f}'


def _dia_al_azar(azar: random.Random, desde: datetime, hasta: datetime) -> date:
    dias = max(1, (hasta.date() - desde.date()).days)
    return desde.date() + timedelta(days=azar.randrange(dias))


def viaje(plantilla: dict[str, str], azar: random.Random, desde: datetime, hasta: datetime,
          regs: dict, zonas_aleatorias: bool = False) -> dict[str, str]:
    """Un viaje inventado a partir de una fila de la muestra, siempre dentro de las reglas."""
    hora = _fecha(plantilla.get(COLUMNA_RECOGIDA))
    recogida = datetime.combine(_dia_al_azar(azar, desde, hasta),
                                hora.time() if hora else datetime.min.time())
    recogida = min(max(recogida, desde), hasta - timedelta(seconds=1))

    distancia = min(_numero(plantilla.get('trip_distance'), 1.0) * azar.uniform(0.75, 1.25),
                    float(regs['distancia_maxima_millas']))
    distancia = max(0.1, distancia)
    segundos = azar.randint(int(DURACION_MINIMA.total_seconds()), int(DURACION_TIPICA.total_seconds()))
    segundos = int(segundos * max(0.6, min(2.0, distancia / 2.0)))
    maxima = int(timedelta(hours=float(regs['duracion_maxima_horas'])).total_seconds())
    llegada = recogida + timedelta(seconds=max(60, min(segundos, maxima - 60)))

    tarifa = max(2.5, _numero(plantilla.get('fare_amount'), 6.0) * azar.uniform(0.85, 1.20))
    extra = max(0.0, _numero(plantilla.get('extra')) * azar.uniform(0.8, 1.2))
    propina = max(0.0, _numero(plantilla.get('tip_amount')) * azar.uniform(0.7, 1.3))
    peajes = max(0.0, _numero(plantilla.get('tolls_amount')) * azar.uniform(0.8, 1.2))
    congestion = max(0.0, _numero(plantilla.get('congestion_surcharge')) * azar.uniform(0.8, 1.2))
    total = tarifa + extra + IMPUESTO_MTA + propina + peajes + RECARGO_MEJORA + congestion

    pasajeros = min(6, max(1, int(_numero(plantilla.get('passenger_count'), 1.0))))
    if azar.random() < 0.08:
        pasajeros = 1
    if zonas_aleatorias:
        origen, destino = (str(azar.randint(int(regs['zona_minima']), int(regs['zona_maxima']))) for _ in range(2))
    else:                                        # zonas de la plantilla: mantienen el mapa de la ciudad realista
        origen, destino = plantilla.get('PULocationID', ''), plantilla.get('DOLocationID', '')

    return {
        'VendorID': plantilla.get('VendorID', ''),
        COLUMNA_RECOGIDA: recogida.strftime(FORMATO_FECHA),
        COLUMNA_LLEGADA: llegada.strftime(FORMATO_FECHA),
        'passenger_count': str(pasajeros),
        'trip_distance': f'{distancia:.1f}',
        'RatecodeID': plantilla.get('RatecodeID', ''),
        'store_and_fwd_flag': plantilla.get('store_and_fwd_flag', ''),
        'PULocationID': origen,
        'DOLocationID': destino,
        'payment_type': plantilla.get('payment_type', ''),
        'fare_amount': _dinero(tarifa),
        'extra': _dinero(extra),
        'mta_tax': _dinero(IMPUESTO_MTA),
        'tip_amount': _dinero(propina),
        'tolls_amount': _dinero(peajes),
        'improvement_surcharge': _dinero(RECARGO_MEJORA),
        'total_amount': _dinero(total),
        'congestion_surcharge': _dinero(congestion),
    }


def _fecha(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        return datetime.strptime(texto.strip(), FORMATO_FECHA)
    except ValueError:
        return None


def dias_de_la_plantilla(filas: list[dict[str, str]]) -> tuple[datetime, datetime] | None:
    """Primer y último día con recogidas legibles en la plantilla (`hasta` no se incluye)."""
    fechas = [f for f in (_fecha(fila.get(COLUMNA_RECOGIDA)) for fila in filas) if f]
    if not fechas:
        return None
    primero = datetime.combine(min(fechas).date(), datetime.min.time())
    return primero, datetime.combine(max(fechas).date(), datetime.min.time()) + timedelta(days=1)


def generar(filas: int, plantilla: Path = PLANTILLA_POR_DEFECTO, semilla: int | None = None,
            desde: datetime | None = None, hasta: datetime | None = None,
            zonas_aleatorias: bool = False) -> tuple[list[str], list[dict[str, str]]]:
    """`filas` viajes inventados con el esquema de la plantilla, listos para enviar o para guardar.

    Por defecto caen en los mismos días que la plantilla; `desde` y `hasta` los reparten por otro
    tramo, siempre dentro de la ventana que admiten las reglas (2020).
    """
    if filas <= 0 or filas > MAXIMO_FILAS:
        raise ValueError(f'el número de viajes tiene que estar entre 1 y {MAXIMO_FILAS:,}')
    columnas, plantillas = leer_plantillas(plantilla)
    regs = reglas()
    minimo, maximo = ventana(regs)
    if desde is None or hasta is None:
        propios = dias_de_la_plantilla(plantillas)
        # La muestra tiene alguna fecha fuera de 2020 (la plataforma las rechaza): el tramo se recorta
        if propios:
            propios = (max(propios[0], minimo), min(propios[1], maximo))
        if not propios or propios[0] >= propios[1]:
            propios = (minimo, maximo)
        desde, hasta = desde or propios[0], hasta or propios[1]
    if desde < minimo or hasta > maximo or desde >= hasta:
        raise ValueError(f'las fechas tienen que ir de {minimo:%Y-%m-%d} a {maximo:%Y-%m-%d} y estar en orden')
    azar = random.Random(semilla)
    generados = [viaje(azar.choice(plantillas), azar, desde, hasta, regs, zonas_aleatorias) for _ in range(filas)]
    generados.sort(key=lambda fila: _fecha(fila[COLUMNA_RECOGIDA]) or datetime.max)
    return columnas, generados


# Formatos de fecha de los ficheros de viajes: TLC (muestra), exportación europea e ISO
FORMATOS_LECTURA = (FORMATO_FECHA, '%Y %b %d %I:%M:%S %p', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S')


def _fecha_y_formato(valor) -> tuple[datetime, str | None] | None:
    """La fecha de una celda y el formato en que venía (None si ya era un datetime)."""
    if isinstance(valor, datetime):
        return valor, None
    if isinstance(valor, str) and valor.strip():
        for formato in FORMATOS_LECTURA:
            try:
                return datetime.strptime(valor.strip(), formato), formato
            except ValueError:
                continue
    return None


def desplazar_a_dia(viajes: list[dict], dia: date) -> list[dict]:
    """Los mismos viajes movidos días enteros para que su día más frecuente pase a ser `dia`.

    Sirve para enviar la muestra (1 de enero) al tiempo real cuando este ya va más adelante: Spark
    descarta lo anterior a la última hora publicada. Se conservan la hora, la duración y el formato de
    cada fecha; las que no se entienden se dejan tal cual (la plataforma las rechazará como siempre).
    """
    columnas = {c for v in viajes[:1] for c in v if c.lower() in (COLUMNA_RECOGIDA, COLUMNA_LLEGADA)}
    recogida = next((c for c in columnas if c.lower() == COLUMNA_RECOGIDA), None)
    if recogida is None:
        return viajes
    dias = Counter(f[0].date() for f in (_fecha_y_formato(v.get(recogida)) for v in viajes) if f)
    if not dias:
        return viajes
    desplazamiento = dia - dias.most_common(1)[0][0]
    movidos = []
    for viaje in viajes:
        nuevo = dict(viaje)
        for columna in columnas:
            leida = _fecha_y_formato(viaje.get(columna))
            if leida:
                fecha, formato = leida
                fecha += desplazamiento
                nuevo[columna] = fecha.strftime(formato) if formato else fecha
        movidos.append(nuevo)
    return movidos


def escribir(ruta: Path, columnas: list[str], filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open('w', newline='', encoding='utf-8') as fichero:
        escritor = csv.DictWriter(fichero, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('filas', type=int, help='cuántos viajes generar')
    p.add_argument('--salida', type=Path, help='CSV de salida (por defecto data/muestra/sinteticos_<filas>.csv)')
    p.add_argument('--plantilla', type=Path, default=PLANTILLA_POR_DEFECTO, help='CSV de referencia')
    p.add_argument('--semilla', type=int, help='para repetir exactamente la misma generación')
    p.add_argument('--desde', type=datetime.fromisoformat, help='primer día (AAAA-MM-DD), dentro de 2020')
    p.add_argument('--hasta', type=datetime.fromisoformat, help='día final, sin incluir')
    p.add_argument('--zonas-aleatorias', action='store_true',
                   help='reparte origen y destino por las 265 zonas en lugar de copiar las de la plantilla')
    a = p.parse_args(argv)
    salida = a.salida or (RAIZ / 'data' / 'muestra' / f'sinteticos_{a.filas}.csv')
    try:
        columnas, filas = generar(a.filas, a.plantilla, a.semilla, a.desde, a.hasta, a.zonas_aleatorias)
        escribir(salida, columnas, filas)
    except (SinPlantillas, ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(f'{len(filas):,} viajes sintéticos en {salida}')
    print(f'Días: de {filas[0][COLUMNA_RECOGIDA]} a {filas[-1][COLUMNA_RECOGIDA]}'
          + (f' · semilla {a.semilla}' if a.semilla is not None else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
