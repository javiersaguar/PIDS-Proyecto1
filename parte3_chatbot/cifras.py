"""Cifras verificadas: cada número que ve el usuario tiene que salir de los datos de la plataforma.

La barrera de `herramientas.tiene_cifras` impide dar cifras cuando no ha llegado ningún dato. Esta va
más allá: aunque haya datos, cada cifra de la respuesta del LLM debe coincidir con un valor devuelto
por la API o con el resumen que calcula el cliente. Así no pasan ni las cifras inventadas ni las
deducidas, como el valor de un grupo enmascarado obtenido restando.

Si alguna cifra no cuadra, la respuesta del LLM se sustituye por los datos tal cual (`respuesta_con_datos`).
"""
from __future__ import annotations

import re
from typing import Any

from herramientas import MESES, enmascarada

MESES_INGLES = 'january|february|march|april|may|june|july|august|september|october|november|december'
# Fechas, horas y códigos: forman parte de la pregunta o de la consulta, no son datos
NO_SON_DATOS = [
    r'\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\b',
    rf'\b\d{{1,2}}\s+de\s+(?:{MESES})(?:\s+de\s+\d{{4}})?\b',
    rf'\b(?:{MESES})\s+de\s+\d{{4}}\b',
    rf'\b(?:{MESES_INGLES})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b',
    r'\b\d{1,2}/\d{1,2}/\d{4}\b',
    r'\b\d{1,2}:\d{2}(?::\d{2})?\b',
    r'\b20(?:19|20|21)\b',                           # el año de los datos
    r'\b(?:http|error|c[oó]digo)\s*:?\s*\d{3}\b',
]
# Reglas públicas de la plataforma (k mínimo, días y filas por consulta): no son datos
CONSTANTES = {10.0, 31.0, 500.0}

NUMERO = re.compile(r'(?<![\w])(\d{1,3}(?:[.,\u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?!\d)')
PALABRA_DE_DATO = (r'(?:%|\$|€|(?:por ciento|percent|viajes?|trayectos?|carreras?|servicios?|taxis?|trips?|'
                   r'rides?|d[oó]lares|dollars?|usd|millas|miles|km|pasajeros?|grupos?)\b)')
DATO_DESPUES = re.compile(r'\s*' + PALABRA_DE_DATO, re.IGNORECASE)
# «Bronx: 5», «| 5 |», «$5», pero también «Staten Island tuvo 5» o «un total de 5»
DATO_ANTES = re.compile(r'([:=|$€]|\b(tuvo|tuvieron|hubo|fueron|fue|son|eran|salieron|sali[oó]|registr\w+|'
                        r'sum\w+|total(\s+de)?|exactamente|aproximadamente|unos|unas))\s*$', re.IGNORECASE)
NUMEROS_EN_LETRA = {'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
                    'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
EN_LETRA = re.compile(r'\b(' + '|'.join(NUMEROS_EN_LETRA) + r')\s+(?:viajes|trayectos|carreras|trips|rides)\b',
                      re.IGNORECASE)
# Un grupo publicado tiene al menos 10 viajes: "1 viaje", "tres viajes" o "un viaje en cada grupo" solo
# pueden salir de deducir un grupo enmascarado
MENOS_QUE_K = re.compile(r'(?<![\d<.,])\b[1-9]\s+(?:viajes?|trayectos?|carreras?|trips?|rides?)\b', re.IGNORECASE)
UNO_POR_GRUPO = re.compile(r'\b(?:un|uno|un solo|un único|exactamente un|one|a single|exactly one)\s+'
                           r'(?:viaje|trayecto|trip|ride)s?\s+(?:cada uno|por grupo|en cada|cada|each|per)\b',
                           re.IGNORECASE)


def sin_fechas(texto: str) -> str:
    limpio = re.sub(r'[*`]', '', texto or '')
    for patron in NO_SON_DATOS:
        limpio = re.sub(patron, ' ', limpio, flags=re.IGNORECASE)
    return limpio


def interpretaciones(token: str) -> list[tuple[float, int]]:
    """Valores posibles de una cifra escrita, con los decimales que lleva.

    "7.182" puede ser 7182 (punto de miles) o 7,182; "2,05" solo puede ser 2,05; "1.234,5" es 1234,5.
    """
    partes = re.split(r'[.,\u00a0\u202f]', token)
    separadores = re.sub(r'\d', '', token)
    if not separadores:
        return [(float(token), 0)]
    if len(set(separadores)) > 1:                    # mezcla: el último separador es el decimal
        return [(float(''.join(partes[:-1]) + '.' + partes[-1]), len(partes[-1]))]
    valores = []
    if all(len(p) == 3 for p in partes[1:]):
        valores.append((float(''.join(partes)), 0))
    if len(partes) == 2 and separadores in '.,':
        valores.append((float(f'{partes[0]}.{partes[1]}'), len(partes[1])))
    return valores


def numeros_en(texto: str) -> set[float]:
    """Todos los valores posibles de las cifras de un texto (sin contar fechas ni horas)."""
    return {v for m in NUMERO.finditer(sin_fechas(texto)) for v, _ in interpretaciones(m.group(1))}


def _recoger(valor: Any, destino: set[float]) -> None:
    if isinstance(valor, bool):
        return
    if isinstance(valor, (int, float)):
        destino.add(float(valor))
    elif isinstance(valor, str):
        destino.update(numeros_en(valor))               # "<10", los motivos de un rechazo…
    elif isinstance(valor, dict):
        for v in valor.values():
            _recoger(v, destino)
    elif isinstance(valor, (list, tuple)):
        for v in valor:
            _recoger(v, destino)


def valores_permitidos(resultados: list, pregunta: str = '') -> set[float]:
    """Todo número que aparece en los resultados, más totales y medias sencillas de cada columna.

    Totales y medias solo cuando no hay grupos enmascarados: sumar lo visible junto a un grupo oculto
    es justo lo que permitiría deducirlo.
    """
    valores = set(CONSTANTES) | numeros_en(pregunta)
    for resultado in resultados:
        _recoger(resultado, valores)
        filas = resultado.get('filas') if isinstance(resultado, dict) else None
        if not filas or any(enmascarada(f) for f in filas):
            continue
        columnas = {k for f in filas for k, v in f.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        for columna in columnas:
            serie = [f[columna] for f in filas if isinstance(f.get(columna), (int, float))]
            valores.add(float(sum(serie)))
            valores.add(sum(serie) / len(serie))
    return valores


def _coincide(valor: float, decimales: int, permitidos: set[float]) -> bool:
    tolerancia = 0.5 * 10 ** -decimales + 1e-9       # "2,1" vale para 2,13; "7.182" solo para 7182
    return any(abs(valor - p) <= tolerancia for p in permitidos)


def cifras_no_justificadas(texto: str, resultados: list, pregunta: str = '') -> list[str]:
    """Cifras de la respuesta que no salen de los datos. Lista vacía = todas verificadas.

    Los enteros pequeños que no acompañan a un dato ("las 8", "3 barrios", "7 días") no se comprueban;
    sí "Bronx: 12", "| 12 |", "Staten Island tuvo 3" o una respuesta que es solo un número. Una cifra de
    viajes menor que 10 nunca vale: ningún grupo publicado la tiene.
    """
    limpio = sin_fechas(texto)
    permitidos = valores_permitidos(resultados, pregunta)
    solo_un_numero = bool(re.fullmatch(r'\W*\d[\d.,]*\W*', limpio.split('_Datos')[0]))
    sueltas = []
    for m in NUMERO.finditer(limpio):
        token = m.group(1)
        valores = interpretaciones(token)
        es_dato = (DATO_DESPUES.match(limpio, m.end()) or DATO_ANTES.search(limpio[max(0, m.start() - 20):m.start()])
                   or solo_un_numero)
        if re.fullmatch(r'\d+', token) and int(token) <= 31 and not es_dato:
            continue
        if not any(_coincide(v, d, permitidos) for v, d in valores):
            sueltas.append(token)
    return sueltas + [c for c in cifras_de_grupos_pequenos(texto) if c not in sueltas]


def cifras_de_grupos_pequenos(texto: str) -> list[str]:
    """Cifras menores que k junto a "viajes": el valor de un grupo que tendría que estar enmascarado."""
    limpio = sin_fechas(texto)
    return [m.group(0) for patron in (MENOS_QUE_K, EN_LETRA, UNO_POR_GRUPO) for m in patron.finditer(limpio)]


# --- los datos tal cual, cuando la respuesta del LLM no es fiable ----------------------------------------

NIVELES = {'hora_zona': 'por hora y zona de origen', 'dia_barrio': 'por día y barrio de origen',
           'od_dia_barrio': 'flujos entre barrios por día'}
COLUMNAS = [('hora', 'Hora'), ('dia', 'Día'), ('zona_origen_nombre', 'Zona de origen'),
            ('barrio_origen', 'Barrio de origen'), ('barrio_destino', 'Barrio de destino'),
            ('n_viajes', 'Viajes'), ('distancia_media', 'Distancia media (millas)'),
            ('importe_medio', 'Importe medio ($)'), ('propina_media', 'Propina media ($)'),
            ('pct_pago_tarjeta', '% pago con tarjeta')]
MAX_FILAS_TABLA = 25


def formato(valor: Any) -> str:
    if isinstance(valor, bool) or valor is None:
        return '—'
    if isinstance(valor, int):
        return f'{valor:,}'.replace(',', '.')
    if isinstance(valor, float):
        return f'{valor:,.2f}'.replace(',', ' ').replace('.', ',').replace(' ', '.')
    if isinstance(valor, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?', valor):
        return valor[:10] if valor[11:16] == '00:00' else valor[:16].replace('T', ' ')
    return str(valor)


def _tabla(resultado: dict) -> str:
    consulta = resultado.get('consulta') or {}
    filas = resultado['filas']
    columnas = [(c, t) for c, t in COLUMNAS if any(f.get(c) is not None for f in filas)]
    if any(c == 'zona_origen_nombre' for c, _ in columnas):
        columnas = [(c, t) for c, t in columnas if c != 'barrio_origen']
    fuente = 'tiempo real' if consulta.get('fuente') == 'tiempo_real' else 'histórico'
    lineas = [f'**Viajes {NIVELES.get(consulta.get("nivel"), "")}** · {fuente} · '
              f'{formato(consulta.get("desde"))} → {formato(consulta.get("hasta"))}', '',
              '| ' + ' | '.join(t for _, t in columnas) + ' |', '|' + '---|' * len(columnas)]
    for fila in filas[:MAX_FILAS_TABLA]:
        celdas = []
        for c, _ in columnas:
            valor = fila.get(c)
            if c == 'hora' and isinstance(valor, str):
                valor = valor[:16].replace('T', ' ')
            elif c == 'dia' and isinstance(valor, str):
                valor = valor[:10]
            celdas.append(formato(valor))
        lineas.append('| ' + ' | '.join(celdas) + ' |')
    if len(filas) > MAX_FILAS_TABLA:
        lineas.append(f'\nSe muestran las primeras {MAX_FILAS_TABLA} de {len(filas)} filas.')
    resumen = resultado.get('resumen') or {}
    if resumen.get('total_viajes') is not None:
        lineas.append(f'\nTotal: {formato(resumen["total_viajes"])} viajes.')
    ocultos = resultado.get('grupos_enmascarados') or 0
    if ocultos:
        grupos = '1 grupo está enmascarado' if ocultos == 1 else f'{ocultos} grupos están enmascarados'
        lineas.append(f'\n{grupos} por privacidad: no se muestran sus cifras ni se suman a ningún total.')
    return '\n'.join(lineas)


def todo_enmascarado(resultados: list) -> bool:
    """¿Todas las filas devueltas en el turno son grupos enmascarados? (Y hay alguna.)"""
    filas = [f for r in resultados if isinstance(r, dict) for f in r.get('filas') or []]
    return bool(filas) and all(enmascarada(f) for f in filas)


def respuesta_enmascarada(resultados: list) -> str:
    """Cuando todo está enmascarado no hay cifras que contar: la respuesta se da sin el LLM."""
    tablas = respuesta_con_datos(resultados) or ''
    return tablas.replace('Estos son los datos publicados para tu consulta:',
                          'Todos los grupos de esta consulta están enmascarados por privacidad (tienen menos de 10 '
                          'viajes, o se ocultan para que no se puedan deducir otros), así que no se muestran sus '
                          'cifras:', 1)


def respuesta_con_datos(resultados: list) -> str | None:
    """Las filas devueltas por la API en tablas, sin pasar por el LLM. None si no hay filas."""
    bloques, vistas = [], set()
    for resultado in resultados:
        if not (isinstance(resultado, dict) and resultado.get('filas')):
            continue
        clave = repr(sorted((resultado.get('consulta') or {}).items(), key=str))
        if clave not in vistas:
            vistas.add(clave)
            bloques.append(_tabla(resultado))
    if not bloques:
        return None
    return 'Estos son los datos publicados para tu consulta:\n\n' + '\n\n'.join(bloques)
