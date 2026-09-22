"""Los cuadros de Grafana dentro del portal, dibujados por la SPA (sección Observabilidad).

La fuente es la misma que la de Grafana: los JSON de `parte2_plataforma/observabilidad/grafana/dashboards` (los
genera `generar.py`). De cada cuadro se saca una descripción sencilla de sus paneles (tipo, título, posición en la
rejilla de 24 columnas, unidad, colores y umbrales) y el BFF ejecuta en Prometheus **solo** las consultas que hay
en esos ficheros: la SPA pide un cuadro por su uid, nunca una consulta. Así funciona igual en el equipo, por el
túnel de la web pública y, con datos grabados, en la demostración.

  - stat: consulta instantánea; si no depende del periodo (`$__range`), además una serie corta para la chispa.
  - serie: consulta de rango sobre el periodo del cuadro, unos 60 puntos por serie.
  - barras y tarta: consulta instantánea, un valor por serie.
  - alertas: el estado de las reglas de Grafana (`/api/prometheus/grafana/api/v1/rules`, lectura anónima).
  - texto: el markdown del panel.

Prometheus o Grafana caídos no rompen nada: el panel lleva `error` y la página lo dice. Cada cuadro se guarda
unos segundos en memoria: la página lo refresca cada 30 s, como Grafana.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from ..configuracion import RAIZ
from .acceso import CacheTTL, SIN_VALOR, ServicioNoDisponible
from .prometheus import ClientePrometheus

CARPETA = RAIZ / 'parte2_plataforma' / 'observabilidad' / 'grafana' / 'dashboards'
PUNTOS_SERIE = 60
PUNTOS_CHISPA = 24
PASO_MINIMO_S = 15                   # el intervalo de sondeo de Prometheus
TTL_CUADRO = 10.0
TIEMPO_GRAFANA = 5.0
TIPOS = {'row': 'fila', 'stat': 'stat', 'timeseries': 'serie', 'bargauge': 'barras', 'piechart': 'tarta',
         'text': 'texto', 'alertlist': 'alertas'}
CACHE = CacheTTL(TTL_CUADRO)


# --- lógica pura -------------------------------------------------------------------------------------------

def segundos(periodo: str) -> int:
    """`6h` → 21600; admite s, m, h y d."""
    numero, unidad = re.fullmatch(r'(\d+)([smhd])', periodo.strip()).groups()
    return int(numero) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unidad]


def expresion(expr: str, periodo: str) -> str:
    """La consulta con la variable de Grafana `$__range` sustituida por el periodo del cuadro."""
    return expr.replace('$__range', periodo)


def leyenda(formato: str, etiquetas: dict[str, str]) -> str:
    """`{{cliente}} · {{resultado}}` con las etiquetas de la serie; sin formato, la primera etiqueta que no sea el nombre."""
    if formato:
        texto = re.sub(r'\{\{\s*(\w+)\s*\}\}', lambda m: etiquetas.get(m.group(1), ''), formato)
        texto = re.sub(r'\s+', ' ', texto).strip(' ·')
        if texto:
            return texto
    resto = [v for k, v in etiquetas.items() if k != '__name__']
    return resto[0] if resto else 'valor'


def _umbrales(campo: dict) -> list[dict]:
    pasos = (campo.get('thresholds') or {}).get('steps') or []
    return [{'color': p.get('color'), 'desde': p.get('value')} for p in pasos]


def _mapeos(campo: dict) -> dict[str, dict]:
    salida = {}
    for mapeo in campo.get('mappings') or []:
        if mapeo.get('type') == 'value':
            for valor, opcion in (mapeo.get('options') or {}).items():
                salida[str(valor)] = {'texto': opcion.get('text'), 'color': opcion.get('color')}
    return salida


def _colores(configuracion: dict) -> dict[str, str]:
    salida = {}
    for sustitucion in configuracion.get('overrides') or []:
        if (sustitucion.get('matcher') or {}).get('id') != 'byName':
            continue
        for propiedad in sustitucion.get('properties') or []:
            if propiedad.get('id') == 'color':
                salida[sustitucion['matcher']['options']] = propiedad['value'].get('fixedColor')
    return salida


def describir_panel(panel: dict) -> dict | None:
    """Lo que la SPA necesita para dibujar un panel, y sus consultas (que no salen del BFF)."""
    tipo = TIPOS.get(panel.get('type', ''))
    if tipo is None:
        return None
    posicion = panel.get('gridPos') or {}
    configuracion = panel.get('fieldConfig') or {}
    campo = configuracion.get('defaults') or {}
    return {
        'id': panel.get('id'),
        'tipo': tipo,
        'titulo': panel.get('title', ''),
        'descripcion': panel.get('description', ''),
        'x': posicion.get('x', 0), 'y': posicion.get('y', 0), 'ancho': posicion.get('w', 24), 'alto': posicion.get('h', 8),
        'unidad': campo.get('unit', 'short'),
        'color': (campo.get('color') or {}).get('fixedColor'),
        'umbrales': _umbrales(campo),
        'mapeos': _mapeos(campo),
        'colores': _colores(configuracion),
        'texto': (panel.get('options') or {}).get('content') if tipo == 'texto' else None,
        '_consultas': [{'expr': t['expr'], 'leyenda': t.get('legendFormat', ''), 'instantanea': bool(t.get('instant'))}
                       for t in panel.get('targets') or [] if t.get('expr')],
    }


def describir_cuadro(cuadro: dict) -> dict:
    periodo = (cuadro.get('time') or {}).get('from', 'now-6h').removeprefix('now-')
    paneles = []
    for panel in cuadro.get('panels') or []:
        for pieza in [panel, *(panel.get('panels') or [])]:
            descrito = describir_panel(pieza)
            if descrito:
                paneles.append(descrito)
    titulo = cuadro.get('title', '').removeprefix('PIDS · ')
    return {'uid': cuadro['uid'], 'titulo': titulo, 'periodo': periodo, 'paneles': paneles}


@lru_cache(maxsize=4)
def cuadros(carpeta: Path = CARPETA) -> dict[str, dict]:
    """Los cuadros provisionados, por uid y en el orden de `generar.py` (plataforma primero)."""
    leidos = [describir_cuadro(json.loads(ruta.read_text(encoding='utf-8'))) for ruta in sorted(carpeta.glob('*.json'))]
    orden = ['pids-plataforma', 'pids-privacidad', 'pids-chatbots', 'pids-kafka', 'pids-spark', 'pids-mongo', 'pids-s3',
             'pids-tiempo-real']
    leidos.sort(key=lambda c: orden.index(c['uid']) if c['uid'] in orden else len(orden))
    return {c['uid']: c for c in leidos}


def _numero(texto: Any) -> float | None:
    try:
        valor = float(texto)
    except (TypeError, ValueError):
        return None
    return valor if math.isfinite(valor) else None


def nombres(metricas: list[dict], formato: str) -> list[str]:
    """La leyenda de cada serie, sin repetidas: a las que coinciden se les añade la etiqueta que las distingue (la
    instancia si vale, como en `spark-workers · spark-worker-1:8081`) o, si ninguna lo hace, un número."""
    salida = [leyenda(formato, m) for m in metricas]
    for nombre in set(salida):
        iguales = [j for j, otro in enumerate(salida) if otro == nombre]
        if len(iguales) < 2:
            continue
        claves = sorted({k for j in iguales for k in metricas[j]} - {'__name__'}, key=lambda k: (k != 'instance', k))
        distintiva = next((k for k in claves if len({metricas[j].get(k) for j in iguales}) == len(iguales)), None)
        for n, j in enumerate(iguales, start=1):
            salida[j] = f'{nombre} · {metricas[j].get(distintiva)}' if distintiva else f'{nombre} ({n})'
    return salida


def valores_instantaneos(vector: list[dict], formato: str) -> list[dict]:
    etiquetas = nombres([m.get('metric', {}) for m in vector], formato)
    return [{'nombre': nombre, 'valor': _numero(m.get('value', [None, None])[1])} for nombre, m in zip(etiquetas, vector)]


def series_de_rango(matriz: list[dict], formato: str) -> list[dict]:
    etiquetas = nombres([m.get('metric', {}) for m in matriz], formato)
    return [{'nombre': nombre, 'puntos': [[float(t), _numero(v)] for t, v in m.get('values', [])]}
            for nombre, m in zip(etiquetas, matriz)]


def alertas_de_reglas(cuerpo: dict) -> list[dict]:
    """Las reglas de Grafana del proyecto con su estado (`firing`, `pending`, `inactive`)."""
    salida = []
    for grupo in (cuerpo.get('data') or {}).get('groups') or []:
        for regla in grupo.get('rules') or []:
            if regla.get('type', 'alerting') != 'alerting':
                continue
            salida.append({'nombre': regla.get('name', '').removeprefix('PIDS · '),
                           'estado': regla.get('state', 'inactive'),
                           'resumen': (regla.get('annotations') or {}).get('summary', '')})
    orden = {'firing': 0, 'pending': 1}
    return sorted(salida, key=lambda a: (orden.get(a['estado'], 2), a['nombre']))


# --- datos -----------------------------------------------------------------------------------------------------

async def _datos_panel(prometheus: ClientePrometheus, http: httpx.AsyncClient, grafana_url: str, panel: dict,
                       periodo: str, ahora: float) -> dict:
    tipo = panel['tipo']
    try:
        if tipo == 'alertas':
            respuesta = await http.get(f'{grafana_url.rstrip("/")}/api/prometheus/grafana/api/v1/rules',
                                       timeout=TIEMPO_GRAFANA)
            if respuesta.status_code != 200:
                raise ServicioNoDisponible('Grafana', f'ha respondido HTTP {respuesta.status_code}')
            return {'alertas': alertas_de_reglas(respuesta.json())}
        if not panel['_consultas'] or tipo in ('fila', 'texto'):
            return {}
        consulta = panel['_consultas'][0]
        expr = expresion(consulta['expr'], periodo)
        if tipo == 'serie':
            duracion = segundos(periodo)
            paso = max(PASO_MINIMO_S, duracion // PUNTOS_SERIE)
            matriz = await prometheus.rango(expr, ahora - duracion, ahora, paso)
            return {'series': series_de_rango(matriz, consulta['leyenda'])}
        datos = {'valores': valores_instantaneos(await prometheus.instantanea(expr), consulta['leyenda'])}
        if tipo == 'stat' and '$__range' not in consulta['expr']:
            duracion = min(segundos(periodo), 3 * 3600)
            paso = max(PASO_MINIMO_S, duracion // PUNTOS_CHISPA)
            matriz = await prometheus.rango(expr, ahora - duracion, ahora, paso)
            if matriz:
                datos['chispa'] = [v for _, v in series_de_rango(matriz[:1], '')[0]['puntos'] if v is not None]
        return datos
    except ServicioNoDisponible as error:
        return {'error': f'{error.servicio} no responde'}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {'error': 'Respuesta no válida'}


async def cuadro_con_datos(uid: str, http: httpx.AsyncClient, prometheus_url: str, grafana_url: str) -> dict | None:
    """El cuadro `uid` con los datos de cada panel (cacheado unos segundos), o None si no existe."""
    descrito = cuadros().get(uid)
    if descrito is None:
        return None
    guardado = CACHE.obtener(uid)
    if guardado is not SIN_VALOR:
        return guardado
    ahora = time.time()
    prometheus = ClientePrometheus(http, prometheus_url)
    datos = await asyncio.gather(*(_datos_panel(prometheus, http, grafana_url, panel, descrito['periodo'], ahora)
                                   for panel in descrito['paneles']))
    paneles = [{**{k: v for k, v in panel.items() if not k.startswith('_')}, **extra}
               for panel, extra in zip(descrito['paneles'], datos, strict=True)]
    con_datos = [p for p in paneles if p['tipo'] not in ('fila', 'texto')]
    resultado = {'uid': uid, 'titulo': descrito['titulo'], 'periodo': descrito['periodo'], 'actualizado': ahora,
                 'disponible': not con_datos or not all('error' in p for p in con_datos), 'paneles': paneles}
    return CACHE.guardar(uid, resultado)


def lista() -> list[dict]:
    return [{'uid': c['uid'], 'titulo': c['titulo'], 'periodo': c['periodo']} for c in cuadros().values()]
