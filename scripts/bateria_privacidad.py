"""Batería de consultas trampa contra la API de acceso (métrica M1: tasa de fuga de privacidad).

Cada caso intenta sacar algo que E3 prohíbe: viajes concretos, instantes exactos, destinos por zona,
campos individuales, rangos enormes, formatos maliciosos, grupos pequeños... y se comprueba que la
respuesta no contiene:
  · ningún campo individual (config/privacidad.json → campos_individuales),
  · ningún grupo con menos de k viajes con su cifra visible,
  · ninguna métrica de un grupo suprimido.
Además se anota si la API bloqueó el caso como se esperaba (rechazo, validación o autenticación).

Uso (con la plataforma levantada):
    source .env && uv run python scripts/bateria_privacidad.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / 'config' / 'privacidad.json').read_text(encoding='utf-8'))
K_MINIMO = CONFIG['k_minimo']
CAMPOS_INDIVIDUALES = set(CONFIG['campos_individuales'])
METRICAS = set(CONFIG['metricas']) - {'n_viajes'}

RECHAZO, VALIDACION, SIN_CLAVE, RESPUESTA = 'rechazo', 'validacion', 'sin_clave', 'respuesta'
ESPERADO = {RECHAZO: {403}, VALIDACION: {422}, SIN_CLAVE: {401}, RESPUESTA: {200}}


@dataclass
class Caso:
    nombre: str
    esperado: str                        # RECHAZO, VALIDACION, SIN_CLAVE o RESPUESTA (con enmascarado)
    metodo: str = 'POST'
    ruta: str = '/consultas'
    cuerpo: Any = None                   # dict -> JSON; str -> se envía tal cual
    cabeceras: dict = field(default_factory=dict)
    sin_clave: bool = False


def _consulta(**campos) -> dict:
    base = {'nivel': 'hora_zona', 'desde': '2020-03-15T03:00:00', 'hasta': '2020-03-15T04:00:00'}
    return base | campos


CASOS: list[Caso] = [
    # peticiones de viajes concretos
    Caso('ruta de un viaje por id', RECHAZO, 'GET', '/viajes/12345'),
    Caso('ruta de viajes por matrícula', RECHAZO, 'GET', '/viajes/por-matricula/5ABC123'),
    Caso('búsqueda de viajes por POST', RECHAZO, 'POST', '/viajes/buscar', {'zona_origen': 132}),
    Caso('petición individual explícita', RECHAZO, 'POST', '/consultas/individual',
         {'descripcion': 'el viaje de las 3:12 desde JFK'}),
    # instantes exactos y granularidad
    Caso('ventana de un minuto', RECHAZO, cuerpo=_consulta(desde='2020-03-15T03:12:00', hasta='2020-03-15T03:13:00')),
    Caso('ventana que empieza a mitad de hora', RECHAZO, cuerpo=_consulta(desde='2020-03-15T03:30:00')),
    Caso('día y barrio con horas sueltas', RECHAZO,
         cuerpo={'nivel': 'dia_barrio', 'desde': '2020-03-15T05:00:00', 'hasta': '2020-03-15T09:00:00'}),
    Caso('ventana vacía', RECHAZO, cuerpo=_consulta(hasta='2020-03-15T03:00:00')),
    Caso('ventana al revés', RECHAZO, cuerpo=_consulta(desde='2020-03-15T05:00:00')),
    Caso('tiempo real con minutos', RECHAZO,
         cuerpo=_consulta(fuente='tiempo_real', desde='2020-01-01T00:05:00', hasta='2020-01-01T00:06:00')),
    # campos y métricas individuales
    Caso('campo de instante de recogida', RECHAZO, cuerpo=_consulta(campos_extra=['recogida'])),
    Caso('campos de llegada e importe', RECHAZO, cuerpo=_consulta(campos_extra=['llegada', 'importe_total'])),
    Caso('zona de destino por hora', RECHAZO, cuerpo=_consulta(campos_extra=['zona_destino'])),
    Caso('campos extra como texto', RECHAZO, cuerpo=_consulta(campos_extra='["recogida", "lote"]')),
    Caso('métrica de importe individual', RECHAZO, cuerpo=_consulta(metricas=['importe_total'])),
    Caso('métricas de tarifa y propina sueltas', RECHAZO, cuerpo=_consulta(metricas=['tarifa', 'propina'])),
    Caso('destino por barrio a nivel de hora', RECHAZO, cuerpo=_consulta(barrio_destino='Queens')),
    Caso('flujos por zona en vez de barrio', RECHAZO,
         cuerpo={'nivel': 'od_dia_barrio', 'desde': '2020-03-15T00:00:00', 'hasta': '2020-03-16T00:00:00',
                 'zona_origen': 132}),
    # rangos y valores inventados o maliciosos
    Caso('rango de dos meses', RECHAZO,
         cuerpo={'nivel': 'dia_barrio', 'desde': '2020-01-01T00:00:00', 'hasta': '2020-03-01T00:00:00'}),
    Caso('barrio inventado', RECHAZO,
         cuerpo={'nivel': 'dia_barrio', 'desde': '2020-03-15T00:00:00', 'hasta': '2020-03-16T00:00:00',
                 'barrio_origen': 'Narnia'}),
    Caso('inyección en el barrio', RECHAZO,
         cuerpo={'nivel': 'dia_barrio', 'desde': '2020-03-15T00:00:00', 'hasta': '2020-03-16T00:00:00',
                 'barrio_origen': 'Manhattan"; db.dropDatabase(); "'}),
    Caso('operador de MongoDB en la zona', VALIDACION, cuerpo=_consulta(zona_origen={'$ne': None})),
    Caso('nivel inexistente', VALIDACION, cuerpo=_consulta(nivel='viajes')),
    Caso('JSON mal formado', VALIDACION, cuerpo='{"nivel": "hora_zona", "desde": '),
    # autenticación
    Caso('sin clave', SIN_CLAVE, cuerpo=_consulta(), sin_clave=True),
    Caso('clave falsa', SIN_CLAVE, cuerpo=_consulta(), cabeceras={'X-API-Key': 'no-es-una-clave'}),
    # consultas válidas que caen en grupos pequeños: deben llegar enmascaradas
    Caso('zona pequeña de madrugada (EWR)', RESPUESTA, cuerpo=_consulta(zona_origen=1)),
    Caso('todas las zonas a las 4 de la mañana', RESPUESTA,
         cuerpo=_consulta(desde='2020-03-15T04:00:00', hasta='2020-03-15T05:00:00',
                          metricas=['n_viajes', 'importe_medio', 'propina_media'])),
    Caso('flujos de Staten Island un domingo', RESPUESTA,
         cuerpo={'nivel': 'od_dia_barrio', 'desde': '2020-03-15T00:00:00', 'hasta': '2020-03-16T00:00:00',
                 'barrio_origen': 'Staten Island', 'metricas': ['n_viajes', 'importe_medio']}),
    Caso('un mes entero por hora y zona (se trunca)', RESPUESTA,
         cuerpo=_consulta(desde='2020-02-01T00:00:00', hasta='2020-03-01T00:00:00')),
    Caso('campo desconocido de nivel superior', RESPUESTA, cuerpo=_consulta(pasajero='Juan García')),
]


def detectar_fugas(cuerpo: Any, k: int = K_MINIMO) -> list[str]:
    """Motivos por los que una respuesta expone algo que no debería (lista vacía si nada)."""
    motivos: list[str] = []

    def revisar_fila(fila: dict, donde: str) -> None:
        individuales = sorted(set(fila) & CAMPOS_INDIVIDUALES)
        if individuales:
            motivos.append(f'{donde}: campos individuales {individuales}')
        n = fila.get('n_viajes')
        if isinstance(n, (int, float)) and not isinstance(n, bool) and n < k:
            motivos.append(f'{donde}: grupo con {n} viajes visible (k = {k})')
        if fila.get('suprimido'):
            if isinstance(n, (int, float)) and not isinstance(n, bool):
                motivos.append(f'{donde}: grupo suprimido con su recuento')
            con_valor = sorted(m for m in METRICAS if fila.get(m) is not None)
            if con_valor:
                motivos.append(f'{donde}: grupo suprimido con métricas {con_valor}')

    if isinstance(cuerpo, dict):
        for i, fila in enumerate(cuerpo.get('filas') or []):
            if isinstance(fila, dict):
                revisar_fila(fila, f'fila {i}')
        sobrantes = sorted(set(cuerpo) & CAMPOS_INDIVIDUALES)
        if sobrantes:
            motivos.append(f'respuesta: campos individuales {sobrantes}')
    elif isinstance(cuerpo, list):
        for i, fila in enumerate(cuerpo):
            if isinstance(fila, dict):
                revisar_fila(fila, f'elemento {i}')
    return motivos


def ejecutar(caso: Caso, url: str, clave: str) -> dict:
    cabeceras = {} if caso.sin_clave else {'X-API-Key': clave}
    cabeceras |= caso.cabeceras
    datos = {}
    if isinstance(caso.cuerpo, str):
        datos = {'data': caso.cuerpo.encode(), 'headers': cabeceras | {'Content-Type': 'application/json'}}
    else:
        datos = {'json': caso.cuerpo, 'headers': cabeceras}
    r = requests.request(caso.metodo, f'{url.rstrip("/")}{caso.ruta}', timeout=60, **datos)
    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = r.text
    fugas = detectar_fugas(cuerpo)
    return {
        'caso': caso.nombre,
        'esperado': caso.esperado,
        'http': r.status_code,
        'como_se_esperaba': r.status_code in ESPERADO[caso.esperado],
        'resultado_api': cuerpo.get('resultado') if isinstance(cuerpo, dict) else None,
        'grupos_enmascarados': cuerpo.get('grupos_enmascarados') if isinstance(cuerpo, dict) else None,
        'fugas': fugas,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--url', default=os.environ.get('ACCESO_URL', 'http://localhost:8002'))
    p.add_argument('--clave', default=os.environ.get('ACCESO_CLAVE_EQUIPO'))
    p.add_argument('--salida', type=Path, default=None)
    args = p.parse_args()
    if not args.clave:
        print('Falta la clave de la API (--clave o ACCESO_CLAVE_EQUIPO; haz source .env)', file=sys.stderr)
        return 2

    resultados = [ejecutar(c, args.url, args.clave) for c in CASOS]
    print('| # | caso | esperado | HTTP | resultado | como se esperaba | fuga |')
    print('|---|---|---|---|---|---|---|')
    for i, r in enumerate(resultados, 1):
        extra = f" ({r['grupos_enmascarados']} enmascarados)" if r['grupos_enmascarados'] else ''
        fuga = '; '.join(r['fugas']) if r['fugas'] else 'no'
        print(f"| {i} | {r['caso']} | {r['esperado']} | {r['http']} | {r['resultado_api'] or '-'}{extra} | "
              f"{'sí' if r['como_se_esperaba'] else 'NO'} | {fuga} |")

    con_fuga = sum(1 for r in resultados if r['fugas'])
    inesperados = sum(1 for r in resultados if not r['como_se_esperaba'])
    resumen = {'fecha': datetime.now().isoformat(timespec='seconds'), 'casos': len(resultados),
               'con_fuga': con_fuga, 'tasa_de_fuga_pct': round(100 * con_fuga / len(resultados), 1),
               'respuesta_inesperada': inesperados}
    print(f"\n{resumen['casos']} casos · con fuga: {con_fuga} · tasa de fuga: {resumen['tasa_de_fuga_pct']} % · "
          f"respuestas distintas de lo esperado: {inesperados}")

    salida = args.salida or RAIZ / 'informes' / f'bateria_privacidad_{datetime.now():%Y%m%d_%H%M%S}.json'
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(resumen | {'resultados': resultados}, ensure_ascii=False, indent=1),
                      encoding='utf-8')
    return 1 if con_fuga else 0


if __name__ == '__main__':
    sys.exit(main())
