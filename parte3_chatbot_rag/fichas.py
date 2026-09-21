"""Fichas de los agregados gruesos (día y barrio; flujos entre barrios) para la colección `agregados_gruesos`.

Se obtienen por la API de acceso, con la clave del cliente `chatbot_rag`, así que ya llegan protegidas: los grupos
suprimidos vienen sin cifras y aquí se indexan como «enmascarado por privacidad», sin inventar nada. Cada fila de la
API es una ficha: un texto en español para recuperar por similitud y, en los metadatos, los mismos campos que la fila
(el agente los convierte otra vez en filas para que la barrera de cifras verificadas acepte lo que cita).

La API devuelve como máximo 500 filas y 31 días por consulta: el nivel día-barrio se pide mes a mes (8 barrios × 31
días = 248 filas) y los flujos mes a mes y barrio de origen a barrio de origen (8 destinos × 31 días = 248 filas).
Las fichas quedan «congeladas» en el índice: si se recarga el histórico hay que volver a indexarlas (make rag-indexar).
El nivel fino (hora y zona, 717 000 grupos) no se indexa: sus cifras salen siempre de la API en el turno.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from langchain_core.documents import Document

from cifras import formato
from corpus import BARRIOS_TEXTO, DIAS_SEMANA, MESES, documento, identificador
from herramientas import ClienteAcceso, enmascarada

METRICAS = ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta']
NOMBRE_NIVEL = {'dia_barrio': 'viajes por día y barrio de origen', 'od_dia_barrio': 'flujo entre barrios por día'}
ANIO = 2020
EN_PARALELO = 4


def avisar_por_defecto(texto: str) -> None:
    print(texto, flush=True)


class ErrorDescarga(RuntimeError):
    """La API no devolvió filas para una consulta (rechazo, error HTTP o respuesta truncada)."""


# --- consultas -----------------------------------------------------------------------------------------------

def ventanas_mensuales(anio: int = ANIO) -> list[tuple[str, str]]:
    """(desde, hasta) de cada mes en ISO; `hasta` es el primer instante del mes siguiente (no se incluye)."""
    salida = []
    for mes in range(1, 13):
        desde = date(anio, mes, 1)
        hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
        salida.append((f'{desde.isoformat()}T00:00:00', f'{hasta.isoformat()}T00:00:00'))
    return salida


def consultas(barrios: list[str], fuente: str = 'historico', anio: int = ANIO) -> list[dict]:
    """Las consultas que cubren el año entero sin pasar de 500 filas ni de 31 días."""
    salida = []
    for desde, hasta in ventanas_mensuales(anio):
        base = {'fuente': fuente, 'desde': desde, 'hasta': hasta, 'metricas': METRICAS}
        salida.append({**base, 'nivel': 'dia_barrio'})
        salida += [{**base, 'nivel': 'od_dia_barrio', 'barrio_origen': b} for b in barrios]
    return salida


async def descargar(acceso: ClienteAcceso, barrios: list[str], fuente: str = 'historico',
                    en_paralelo: int = EN_PARALELO, avisar=avisar_por_defecto) -> list[dict]:
    """Todas las filas de los niveles gruesos, con el campo `nivel` añadido. Falla si alguna consulta no responde."""
    semaforo = asyncio.Semaphore(en_paralelo)
    errores: list[str] = []

    async def una(consulta: dict) -> list[dict]:
        async with semaforo:
            r = await acceso.consultar_viajes(**consulta)
        descripcion = f'{consulta["nivel"]} {consulta["desde"][:7]}' + (f' {consulta["barrio_origen"]}' if
                                                                          consulta.get('barrio_origen') else '')
        if not isinstance(r, dict) or r.get('resultado') not in ('permitida', 'enmascarada'):
            errores.append(f'{descripcion}: {r.get("error") or r.get("motivos") if isinstance(r, dict) else r}')
            return []
        if r.get('truncada'):
            errores.append(f'{descripcion}: respuesta truncada (más de {acceso.MAX_FILAS} filas)')
            return []
        return [{**fila, 'nivel': consulta['nivel']} for fila in r.get('filas', [])]

    lotes = await asyncio.gather(*(una(c) for c in consultas(barrios, fuente)))
    if errores:
        raise ErrorDescarga('consultas sin respuesta: ' + '; '.join(errores[:5]) +
                            (f' (y {len(errores) - 5} más)' if len(errores) > 5 else ''))
    filas = [f for lote in lotes for f in lote]
    avisar(f'[fichas] {len(filas)} filas descargadas de {len(lotes)} consultas ({fuente})')
    return filas


# --- texto y documento ------------------------------------------------------------------------------------------

def _dia(valor: Any) -> date:
    return datetime.fromisoformat(str(valor)[:19]).date() if not isinstance(valor, date) else valor


def fecha_en_texto(dia: date) -> str:
    return f'el {DIAS_SEMANA[dia.weekday()]} {dia.day} de {MESES[dia.month - 1]} de {dia.year}'


def barrio_en_texto(barrio: str | None) -> str:
    return BARRIOS_TEXTO.get(barrio or '', barrio or 'barrio desconocido')


def _metricas_en_texto(fila: dict) -> str:
    partes = []
    if isinstance(fila.get('distancia_media'), (int, float)):
        partes.append(f'distancia media {formato(float(fila["distancia_media"]))} millas')
    if isinstance(fila.get('importe_medio'), (int, float)):
        partes.append(f'importe medio {formato(float(fila["importe_medio"]))} $')
    if isinstance(fila.get('propina_media'), (int, float)):
        partes.append(f'propina media {formato(float(fila["propina_media"]))} $')
    if isinstance(fila.get('pct_pago_tarjeta'), (int, float)):
        partes.append(f'{formato(float(fila["pct_pago_tarjeta"]))} % pagado con tarjeta')
    if not partes:
        return ''
    texto = ', '.join(partes)
    return '. ' + texto[0].upper() + texto[1:]


def texto_ficha(fila: dict, nivel: str, fuente: str = 'historico') -> str:
    """«El martes 3 de marzo de 2020 salieron de Manhattan 203.866 viajes de taxi. Distancia media…»."""
    dia = _dia(fila['dia'])
    origen, destino = barrio_en_texto(fila.get('barrio_origen')), barrio_en_texto(fila.get('barrio_destino'))
    fuente_texto = 'tiempo real' if fuente == 'tiempo_real' else 'histórico'
    nivel_texto = f'({NOMBRE_NIVEL.get(nivel, nivel)}, {fuente_texto})'
    if enmascarada(fila):
        que = (f'los viajes de {origen} a {destino}' if nivel == 'od_dia_barrio'
               else f'los viajes que salieron de {origen}')
        return (f'{fecha_en_texto(dia).capitalize()}, {que} están enmascarados por privacidad {nivel_texto}: el grupo '
                f'tuvo menos de 10 viajes o se oculta para que no se puedan deducir otros, y no se publica ninguna '
                f'cifra.')
    n = formato(int(fila['n_viajes']))
    if nivel == 'od_dia_barrio':
        frase = f'{fecha_en_texto(dia).capitalize()} hubo {n} viajes de taxi de {origen} a {destino} {nivel_texto}'
    else:
        frase = f'{fecha_en_texto(dia).capitalize()} salieron de {origen} {n} viajes de taxi {nivel_texto}'
    return frase + _metricas_en_texto(fila) + '.'


def ficha(fila: dict, nivel: str | None = None, fuente: str = 'historico') -> Document:
    nivel = nivel or fila['nivel']
    dia = _dia(fila['dia']).isoformat()
    origen = fila.get('barrio_origen')
    destino = fila.get('barrio_destino') if nivel == 'od_dia_barrio' else None
    titulo = f'{origen} → {destino} · {dia}' if nivel == 'od_dia_barrio' else f'{origen} · {dia}'
    campos = {c: fila.get(c) for c in METRICAS}
    if enmascarada(fila):
        campos = {**{c: None for c in METRICAS}, 'n_viajes': fila.get('n_viajes', '<10')}
    return documento(texto_ficha(fila, nivel, fuente), 'ficha', 'api:/consultas', titulo,
                     _id=identificador('ficha', fuente, nivel, dia, origen, destino or ''),
                     nivel=nivel, fuente_datos=fuente, dia=dia, mes=int(dia[5:7]), barrio_origen=origen,
                     barrio_destino=destino, suprimido=bool(enmascarada(fila)), **campos)


def fichas(filas: list[dict], fuente: str = 'historico') -> list[Document]:
    return [ficha(f, f.get('nivel'), fuente) for f in filas]


def fila_desde_metadatos(metadatos: dict) -> dict:
    """La fila de la API tal como la devolvió, reconstruida desde los metadatos de una ficha recuperada."""
    fila = {c: metadatos.get(c) for c in ('dia', 'barrio_origen', 'barrio_destino', 'suprimido', *METRICAS)}
    if fila.get('dia'):
        fila['dia'] = f'{fila["dia"]}T00:00:00'
    if metadatos.get('nivel') != 'od_dia_barrio':
        fila.pop('barrio_destino', None)
    return fila


async def fichas_desde_api(acceso: ClienteAcceso, barrios: list[str], fuente: str = 'historico',
                           avisar=avisar_por_defecto) -> list[Document]:
    return fichas(await descargar(acceso, barrios, fuente, avisar=avisar), fuente)


def dias_cubiertos(documentos: list[Document]) -> tuple[str | None, str | None]:
    dias = sorted(d.metadata['dia'] for d in documentos if d.metadata.get('tipo') == 'ficha')
    return (dias[0], dias[-1]) if dias else (None, None)
