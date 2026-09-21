"""Mide captura → agregado consultable con lotes sintéticos identificables, sin tocar el histórico."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from scripts.informe_auditoria import entorno, fecha_utc  # noqa: E402


def percentil(valores: list[float], q: float) -> float:
    """Interpolación lineal entre posiciones (n-1)*q, incluida la muestra máxima."""
    if not valores or not 0 <= q <= 1:
        raise ValueError('Se necesitan medidas y un percentil entre 0 y 1')
    ordenados = sorted(valores)
    posicion = (len(ordenados) - 1) * q
    bajo, alto = math.floor(posicion), math.ceil(posicion)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (posicion - bajo)


def viaje(hora: datetime, zona: int, indice: int) -> dict:
    recogida = hora + timedelta(minutes=5, seconds=indice)
    return {'VendorID': 1, 'tpep_pickup_datetime': recogida.isoformat(),
            'tpep_dropoff_datetime': (recogida + timedelta(minutes=10)).isoformat(),
            'passenger_count': 1, 'trip_distance': 2.0, 'RatecodeID': 1,
            'store_and_fwd_flag': 'N', 'PULocationID': zona, 'DOLocationID': zona,
            'payment_type': 1, 'fare_amount': 10.0, 'extra': 0.0, 'mta_tax': 0.5,
            'tip_amount': 1.0, 'tolls_amount': 0.0, 'improvement_surcharge': 0.3,
            'congestion_surcharge': 0.0, 'total_amount': 11.8}


def consulta(hora: datetime, zona: int) -> dict:
    return {'fuente': 'tiempo_real', 'nivel': 'hora_zona', 'zona_origen': zona,
            'desde': hora.isoformat(), 'hasta': (hora + timedelta(hours=1)).isoformat(),
            'metricas': ['n_viajes']}


def planificar(inicio: datetime, zona: int, medidas: int, zonas_distintas: bool = False) -> list[dict]:
    """Una combinación hora-zona nueva por medida: horas crecientes en una zona o, con `zonas_distintas`, la
    misma hora en zonas decrecientes (no adelanta la watermark del streaming entre una medida y otra)."""
    if inicio.tzinfo is not None:
        inicio = inicio.astimezone(timezone.utc).replace(tzinfo=None)
    if inicio != inicio.replace(minute=0, second=0, microsecond=0):
        raise ValueError('--inicio debe ser una hora completa')
    if not 1 <= zona <= 265 or medidas < 20:
        raise ValueError('Se requieren al menos 20 medidas y una zona entre 1 y 265')
    if zonas_distintas:
        if zona - medidas + 1 < 1:
            raise ValueError('No hay tantas zonas por debajo de --zona')
        combinaciones = [(inicio, zona - i) for i in range(medidas)]
    else:
        combinaciones = [(inicio + timedelta(hours=i), zona) for i in range(medidas)]
    if any(h.year != 2020 for h, _ in combinaciones):
        raise ValueError('Todas las horas del experimento deben estar dentro de 2020')
    return [consulta(h, z) for h, z in combinaciones]


def filas_consulta(http: httpx.Client, url: str, clave: str, pedida: dict) -> list[dict]:
    respuesta = http.post(f'{url}/consultas', headers={'X-API-Key': clave}, json=pedida)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if datos.get('truncada') or datos.get('resultado') not in ('permitida', 'enmascarada'):
        raise ValueError('La consulta de comprobación no es íntegra')
    return datos['filas']


def trabajo_activo(http: httpx.Client, url: str) -> str:
    respuesta = http.get(f'{url}/json/')
    respuesta.raise_for_status()
    activos = [a for a in respuesta.json().get('activeapps', []) if a.get('name') == 'pids-tiempo-real']
    if len(activos) != 1:
        raise ValueError(f'Se requiere exactamente una aplicación pids-tiempo-real; hay {len(activos)}')
    return activos[0]['id']


def reconocido(filas: list[dict], esperado: int) -> bool:
    if len(filas) != 1:
        return False
    fila = filas[0]
    return fila.get('suprimido') is False and fila.get('n_viajes') == esperado


def resumen(medidas: list[dict]) -> dict:
    valores = [m['latencia_s'] for m in medidas if m.get('estado') == 'publicado']
    return {'medidas': len(medidas), 'publicadas': len(valores),
            'fallidas': len(medidas) - len(valores),
            'p50_s': percentil(valores, .5) if valores else None,
            'p95_s': percentil(valores, .95) if valores else None,
            'maximo_s': max(valores) if valores else None,
            'metodo_percentil': 'interpolación lineal (n-1)*q; solo publicadas; fallidas declaradas aparte'}


def guardar(carpeta: Path, medidas: list[dict], configuracion: dict) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    with (carpeta / 'medidas.csv').open('w', newline='', encoding='utf-8') as fichero:
        campos = ['lote', 'aplicacion', 'hora', 'zona', 'viajes', 'enviado_utc', 'estado',
                  'latencia_s', 'acuse_s', 'limite_inferior_s', 'consultas', 'detalle']
        escritor = csv.DictWriter(fichero, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(medidas)
    salida = {**resumen(medidas), 'configuracion': configuracion}
    (carpeta / 'resumen.json').write_text(json.dumps(salida, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inicio', type=fecha_utc, default=fecha_utc('2020-12-31T00:00:00'),
                   help='Primera hora de viaje (UTC)')
    p.add_argument('--zona', type=int, default=265)
    p.add_argument('--medidas', type=int, default=20)
    p.add_argument('--viajes', type=int, default=15)
    p.add_argument('--sondeo', type=float, default=1.0)
    p.add_argument('--timeout', type=float, default=120.0)
    p.add_argument('--pausa', type=float, default=2.0, help='Espera entre medidas completas, en segundos')
    p.add_argument('--desfase', type=float, default=0.0,
                   help='Espera aleatoria extra (0..DESFASE s) antes de cada envío, para no llegar siempre justo '
                        'después de un trigger; con 30 las llegadas caen en cualquier punto del ciclo')
    p.add_argument('--zonas-distintas', action='store_true',
                   help='Misma hora (--inicio) en zonas decrecientes desde --zona, en vez de horas crecientes')
    p.add_argument('--semilla', type=int, default=None, help='Semilla del desfase aleatorio')
    p.add_argument('--salida', type=Path)
    args = p.parse_args()
    if not 15 <= args.viajes <= 1000 or min(args.sondeo, args.timeout) <= 0 or min(args.pausa, args.desfase) < 0:
        p.error('Viajes entre 15 y 1000; sondeo y timeout positivos; pausa y desfase no negativos')
    azar = random.Random(args.semilla)
    try:
        plan = planificar(args.inicio, args.zona, args.medidas, args.zonas_distintas)
    except ValueError as error:
        p.error(str(error))
    cfg = entorno()
    if not cfg.get('ACCESO_CLAVE_EQUIPO') or not cfg.get('CAPTURA_CLAVE_SIMULADOR'):
        p.error('Faltan las claves de acceso y captura en el entorno o en .env')
    acceso = f'http://127.0.0.1:{cfg.get("PUERTO_ACCESO", "8002")}'
    captura = f'http://127.0.0.1:{cfg.get("PUERTO_CAPTURA", "8001")}'
    spark = f'http://127.0.0.1:{cfg.get("PUERTO_SPARK", "8090")}'
    identificador = 'latencia-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:6]
    salida = args.salida or RAIZ / 'informes' / identificador
    if salida.exists():
        p.error('La carpeta de salida ya existe; usa una nueva para conservar la evidencia')
    if not salida.resolve().is_relative_to((RAIZ / 'informes').resolve()):
        p.error('--salida debe estar dentro de informes/')
    medidas = []
    configuracion = {'inicio': plan[0]['desde'], 'zona': args.zona, 'zonas_distintas': args.zonas_distintas,
                     'medidas_previstas': args.medidas, 'viajes_por_lote': args.viajes, 'sondeo_s': args.sondeo,
                     'timeout_s': args.timeout, 'pausa_s': args.pausa, 'desfase_max_s': args.desfase,
                     'semilla': args.semilla, 'trigger_s': 30,
                     'reloj': 'monotonic; desde antes de POST /viajes hasta fin de consulta que confirma el grupo'}
    try:
        with httpx.Client(timeout=15) as http:
            aplicacion = trabajo_activo(http, spark)
            catalogo = http.get(f'{acceso}/catalogo', headers={'X-API-Key': cfg['ACCESO_CLAVE_EQUIPO']})
            catalogo.raise_for_status()
            if args.viajes < catalogo.json()['k_minimo']:
                raise ValueError('El lote no supera el umbral de privacidad vigente')
            # Se comprueban todas las combinaciones antes de enviar el primer evento.
            for pedida in plan:
                if filas_consulta(http, acceso, cfg['ACCESO_CLAVE_EQUIPO'], pedida):
                    raise ValueError('Hay agregados previos en una combinación del plan; cambia hora o zona')
            for i, pedida in enumerate(plan):
                if trabajo_activo(http, spark) != aplicacion:
                    raise ValueError('La aplicación de Spark ha cambiado durante la medición')
                if filas_consulta(http, acceso, cfg['ACCESO_CLAVE_EQUIPO'], pedida):
                    raise ValueError('La combinación ya tiene datos; se detiene para no mezclar recuentos')
                if args.desfase:
                    time.sleep(azar.uniform(0, args.desfase))
                lote = f'{identificador}-{i + 1:02d}'
                hora = datetime.fromisoformat(pedida['desde'])
                medida = {'lote': lote, 'aplicacion': aplicacion, 'hora': pedida['desde'],
                          'zona': pedida['zona_origen'], 'viajes': args.viajes,
                          'enviado_utc': datetime.now(timezone.utc).isoformat(), 'estado': 'pendiente',
                          'latencia_s': None, 'acuse_s': None, 'limite_inferior_s': 0.0,
                          'consultas': 0, 'detalle': ''}
                medidas.append(medida)
                inicio = time.monotonic()
                respuesta = http.post(f'{captura}/viajes', headers={'X-API-Key': cfg['CAPTURA_CLAVE_SIMULADOR']},
                                      json={'lote': lote, 'viajes': [viaje(hora, pedida['zona_origen'], j)
                                                                      for j in range(args.viajes)]})
                respuesta.raise_for_status()
                if respuesta.json().get('aceptados') != args.viajes:
                    raise ValueError('La captura no confirmó todos los viajes del lote')
                medida['acuse_s'] = time.monotonic() - inicio
                while time.monotonic() - inicio <= args.timeout:
                    consulta_inicio = time.monotonic() - inicio
                    filas = filas_consulta(http, acceso, cfg['ACCESO_CLAVE_EQUIPO'], pedida)
                    medida['consultas'] += 1
                    if reconocido(filas, args.viajes):
                        medida['estado'] = 'publicado'
                        medida['latencia_s'] = time.monotonic() - inicio
                        break
                    medida['limite_inferior_s'] = consulta_inicio
                    time.sleep(args.sondeo)
                else:
                    medida['estado'] = 'timeout'
                    medida['detalle'] = f'No observado en {args.timeout:g} s; medida censurada'
                guardar(salida, medidas, configuracion)
                print(f'{i + 1}/{args.medidas}: {medida["estado"]}, latencia={medida["latencia_s"]}', flush=True)
                if medida['estado'] != 'publicado':
                    break
                if i + 1 < len(plan):
                    time.sleep(args.pausa)
    except (httpx.HTTPError, ValueError) as error:
        if medidas and medidas[-1]['estado'] == 'pendiente':
            medidas[-1]['estado'] = 'error'
            medidas[-1]['detalle'] = type(error).__name__
        configuracion['interrumpida'] = type(error).__name__
        motivo = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(f'Medición interrumpida: {motivo}', flush=True)
    resultado = guardar(salida, medidas, configuracion)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(f'Evidencia: {salida}')
    return 0 if resultado['publicadas'] == args.medidas and resultado['fallidas'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
