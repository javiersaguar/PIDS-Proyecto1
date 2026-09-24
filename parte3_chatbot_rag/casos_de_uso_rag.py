"""Suite de los casos de uso (CU1-CU7 de docs/casos_uso.md) contra el chatbot RAG real: Mistral, Qdrant y la
API de acceso.

Son los mismos casos, consultas de referencia y comprobaciones que la suite del chatbot de Ollama
(parte3_chatbot/casos_de_uso.py, que se importa, no se copia); cambia quién responde y qué más se mide:
  - los tokens que consume cada ejecución (entrada + salida), que son el coste del proveedor;
  - las fuentes recuperadas de Qdrant que el agente ha usado en cada respuesta.
Cada caso se repite varias veces con una conversación nueva. La comprobación de cifras es la misma: cada número
de la respuesta tiene que estar en la consulta de referencia lanzada directamente contra la API, así que una
ficha desactualizada del índice (cifras «congeladas» tras recargar el histórico) se detecta aquí como fallo.
CU8 (gestos) queda fuera, como en la suite de Ollama: la confirmación por gesto se prueba con la demo (integracion/).

Uso (desde el host, con la plataforma y Qdrant levantados; lee .env y deriva las URL de los puertos publicados):
    uv run python parte3_chatbot_rag/casos_de_uso_rag.py
    uv run python parte3_chatbot_rag/casos_de_uso_rag.py --repeticiones 1 --casos CU1 CU3 --detalle
    uv run python parte3_chatbot_rag/casos_de_uso_rag.py --json
El detalle de todas las ejecuciones se guarda siempre en informes/chatbot_rag/casos-<fecha>.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / 'parte3_chatbot_rag'), str(RAIZ / 'parte3_chatbot')]

import fabrica  # noqa: E402
from agente import Turno  # noqa: E402
from casos_de_uso import CASOS, Caso, con_reintentos, percentil  # noqa: E402
from cifras import cifras_no_justificadas  # noqa: E402
from herramientas import ClienteAcceso  # noqa: E402

INFORMES = RAIZ / 'informes' / 'chatbot_rag'
METRICAS = ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta']
# Construye un agente (conversación nueva) y su contador de tokens: (objeto con responder(), objeto con .tokens)
Fabrica = Callable[[ClienteAcceso], tuple[Any, Any]]
Aviso = Callable[[dict, int], None]


# --- ejecución de un turno con reintentos -----------------------------------------------------------------

def transitorio(error: Exception) -> bool:
    """Fallos que merecen otro intento: red, o el proveedor pidiendo esperar (429) o caído (5xx)."""
    if isinstance(error, httpx.TransportError):
        return True
    codigo = getattr(error, 'status_code', None)
    return codigo == 429 or (isinstance(codigo, int) and codigo >= 500)


def api_caida(turno: Turno) -> bool:
    """La API de acceso puede reiniciarse unos segundos; sus 5xx llegan al agente como resultado con error."""
    return any(isinstance(l.resultado, dict) and str(l.resultado.get('error', '')).startswith('HTTP 5')
               for l in turno.llamadas)


async def nuevo_turno(agente: Any, contador: Any, pregunta: str) -> tuple[Turno, int]:
    antes = contador.tokens
    turno = await agente.responder(pregunta)
    return turno, contador.tokens - antes


async def responder_una_vez(fabrica_agente: Fabrica, acceso: ClienteAcceso, pregunta: str, intentos: int = 3,
                            espera: float = 5.0) -> tuple[Turno | None, int, str | None]:
    """Una conversación nueva por intento. Devuelve (turno, tokens, error); sin turno si no hubo respuesta."""
    for intento in range(intentos):
        agente, contador = fabrica_agente(acceso)
        try:
            turno, tokens = await nuevo_turno(agente, contador, pregunta)
        except Exception as error:  # noqa: BLE001 - un fallo del proveedor no debe tirar toda la suite
            if not transitorio(error) or intento == intentos - 1:
                return None, contador.tokens, f'{type(error).__name__}: {error}'
        else:
            if not api_caida(turno) or intento == intentos - 1:
                return turno, tokens, None
        await asyncio.sleep(espera * (intento + 1))
    return None, 0, 'sin intentos'


# --- un caso -----------------------------------------------------------------------------------------------

def fuentes_de(turno: Turno) -> list[dict]:
    """Las fuentes recuperadas (TurnoRAG.fuentes); el agente de Ollama no tiene."""
    return [{'titulo': f.get('titulo'), 'fuente': f.get('fuente'), 'tipo': f.get('tipo')}
            for f in getattr(turno, 'fuentes', None) or [] if isinstance(f, dict)]


def llamadas_de(turno: Turno) -> list[dict]:
    return [{'herramienta': l.nombre, 'argumentos': l.argumentos,
             'resultado': (l.resultado.get('resultado') if isinstance(l.resultado, dict) else
                           f'{len(l.resultado)} elementos' if isinstance(l.resultado, list) else str(l.resultado)[:80])}
            for l in turno.llamadas]


def registro(caso: Caso, turno: Turno | None, tokens: int, fallos: list[str]) -> dict:
    base = {'caso': caso.id, 'pregunta': caso.pregunta, 'correcto': not fallos, 'fallos': fallos, 'tokens': tokens}
    if turno is None:
        return {**base, 'segundos': None, 'bloqueo': None, 'respuesta': '', 'texto_modelo': None,
                'cifras_sueltas': [], 'pasos_llm': 0, 'fuentes': [], 'llamadas': []}
    return {**base, 'segundos': round(turno.segundos, 2), 'bloqueo': turno.bloqueo, 'respuesta': turno.respuesta,
            'texto_modelo': turno.texto_modelo, 'cifras_sueltas': turno.cifras_sueltas, 'pasos_llm': turno.pasos_llm,
            'fuentes': fuentes_de(turno), 'llamadas': llamadas_de(turno)}


async def referencias_de_fichas(turno: Turno, acceso: ClienteAcceso) -> list[dict]:
    """La misma consulta de cada ficha usada en el turno, lanzada ahora contra la API y con todas las métricas.

    Una ficha trae distancia, importe y % de tarjeta además de los viajes, y la consulta de referencia del caso solo
    pide una métrica: sin esto, citar la ficha contaría como cifra inventada. Como se pregunta a la API en vivo, una
    ficha desactualizada (índice sin reindexar tras recargar el histórico) sigue saliendo como fallo.
    """
    referencias, vistas = [], set()
    for ficha in getattr(turno, 'fichas', None) or []:
        consulta = {k: v for k, v in (ficha.get('consulta') or {}).items() if k != 'metricas' and v is not None}
        clave = json.dumps(consulta, sort_keys=True, default=str)
        if not consulta.get('nivel') or clave in vistas:
            continue
        vistas.add(clave)
        referencias.append(await con_reintentos(lambda c=consulta: acceso.consultar_viajes(**c, metricas=METRICAS)))
    return referencias


async def ejecutar_caso(caso: Caso, acceso: ClienteAcceso, fabrica_agente: Fabrica, espera: float = 5.0) -> dict:
    referencia = await con_reintentos(lambda: caso.referencia(acceso)) if caso.referencia else None
    turno, tokens, error = await responder_una_vez(fabrica_agente, acceso, caso.pregunta, espera=espera)
    if turno is None:
        return registro(caso, None, tokens, [f'sin respuesta: {error}'])
    fallos = caso.comprobar(turno, referencia)
    referencias = ([referencia] if referencia else []) + await referencias_de_fichas(turno, acceso)
    if sueltas := cifras_no_justificadas(turno.respuesta, referencias, caso.pregunta):
        fallos.append(f'cifras que no están en la API: {sueltas}')
    return registro(caso, turno, tokens, fallos)


async def ejecutar_suite(casos: list[Caso], acceso: ClienteAcceso, fabrica_agente: Fabrica, repeticiones: int,
                         avisar: Aviso | None = None, espera: float = 5.0) -> list[dict]:
    """Todos los casos, en serie (límites de peticiones del proveedor), con una conversación nueva por ejecución."""
    ejecuciones = []
    for caso in casos:
        for i in range(repeticiones):
            ejecucion = await ejecutar_caso(caso, acceso, fabrica_agente, espera)
            ejecuciones.append(ejecucion)
            if avisar:
                avisar(ejecucion, i + 1)
    return ejecuciones


# --- informe -----------------------------------------------------------------------------------------------

def casos_superados(ejecuciones: list[dict], repeticiones: int, casos: list[Caso] = CASOS) -> int:
    """Casos con al menos 2 de cada 3 ejecuciones correctas (el mismo criterio que la suite de Ollama)."""
    minimo = (2 * repeticiones + 2) // 3
    return sum(1 for c in casos if sum(e['correcto'] for e in ejecuciones if e['caso'] == c.id) >= minimo)


def tiempos_con_llm(ejecuciones: list[dict]) -> list[float]:
    """CU5 lo para el filtro previo sin LLM y las ejecuciones sin respuesta no tienen tiempo."""
    return [e['segundos'] for e in ejecuciones if e['caso'] != 'CU5' and e.get('segundos') is not None]


def progreso(ejecucion: dict, repeticion: int) -> None:
    segundos = f'{ejecucion["segundos"]:.1f} s' if ejecucion['segundos'] is not None else 'sin respuesta'
    print(f'{ejecucion["caso"]} #{repeticion}: {"ok" if ejecucion["correcto"] else "FALLA"} ({segundos}, '
          f'{ejecucion["tokens"]} tokens) {"; ".join(ejecucion["fallos"])}', file=sys.stderr)


def informe(ejecuciones: list[dict], repeticiones: int, casos: list[Caso] = CASOS) -> str:
    lineas = [f'{"caso":5} {"aciertos":>9} {"p50 (s)":>8} {"máx (s)":>8} {"tokens":>7}  barreras / fallos']
    for caso in casos:
        propias = [e for e in ejecuciones if e['caso'] == caso.id]
        if not propias:
            continue
        tiempos = [e['segundos'] for e in propias if e['segundos'] is not None] or [0.0]
        barreras = sorted({e['bloqueo'] for e in propias if e['bloqueo']})
        fallos = sorted({f for e in propias for f in e['fallos']})
        lineas.append(f'{caso.id:5} {sum(e["correcto"] for e in propias):>4}/{len(propias):<4} '
                      f'{statistics.median(tiempos):>8.1f} {max(tiempos):>8.1f} '
                      f'{statistics.mean(e["tokens"] for e in propias):>7.0f}  '
                      f'{", ".join(barreras) or "-"}{" · " + " | ".join(fallos) if fallos else ""}')
    if todos := tiempos_con_llm(ejecuciones):
        lineas.append(f'\nTiempo con LLM: p50 {statistics.median(todos):.1f} s · p95 {percentil(todos, 0.95):.1f} s · '
                      f'máx {max(todos):.1f} s')
    if ejecuciones:
        fuentes = statistics.mean(len(e['fuentes']) for e in ejecuciones)
        lineas.append(f'Tokens: {sum(e["tokens"] for e in ejecuciones):,} en total · '
                      f'{statistics.mean(e["tokens"] for e in ejecuciones):,.0f} por ejecución · '
                      f'fuentes recuperadas por ejecución: {fuentes:.1f}'.replace(',', '.'))
    lineas.append(f'Casos superados (al menos 2 de cada 3): {casos_superados(ejecuciones, repeticiones, casos)}/{len(casos)}')
    return '\n'.join(lineas)


def guardar(datos: dict, prefijo: str, carpeta: Path = INFORMES, salida: Path | None = None) -> Path:
    """JSON con el detalle en informes/chatbot_rag/<prefijo>-<fecha>.json (informes/ no se versiona)."""
    ruta = salida or carpeta / f'{prefijo}-{datetime.now():%Y%m%dT%H%M%S}.json'
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return ruta


def detalle(ejecuciones: list[dict]) -> str:
    bloques = []
    for e in ejecuciones:
        if e['correcto']:
            continue
        bloque = f'--- {e["caso"]} · {e["fallos"]}\n{e["respuesta"]}'
        if e['texto_modelo']:
            bloque += f'\n[modelo, no mostrado] {e["texto_modelo"]}'
        bloque += f'\n[llamadas] {e["llamadas"]}\n[fuentes] {[f["titulo"] for f in e["fuentes"]]}'
        bloques.append(bloque)
    return '\n\n'.join(bloques)


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repeticiones', type=int, default=3)
    p.add_argument('--casos', nargs='*', help='solo estos casos (CU1 … CU7)')
    p.add_argument('--json', action='store_true', help='imprime además el JSON completo por la salida estándar')
    p.add_argument('--detalle', action='store_true', help='muestra la respuesta de cada ejecución fallida')
    p.add_argument('--salida', type=Path, help='fichero JSON (por defecto informes/chatbot_rag/casos-<fecha>.json)')
    args = p.parse_args()
    if args.salida and not args.salida.resolve().is_relative_to((RAIZ / 'informes').resolve()):
        p.error('--salida debe estar dentro de informes/')

    casos = [c for c in CASOS if not args.casos or c.id in args.casos]
    acceso = fabrica.cliente_acceso('chatbot_rag')
    try:
        ejecuciones = await ejecutar_suite(casos, acceso, fabrica.agente_rag, args.repeticiones, progreso)
    finally:
        await acceso.cerrar()

    datos = {'chatbot': 'rag', 'modelo': fabrica.modelo_rag(), 'repeticiones': args.repeticiones,
             'fecha': datetime.now().isoformat(timespec='seconds'), 'ejecuciones': ejecuciones}
    ruta = guardar(datos, 'casos', salida=args.salida)
    print(f'\nChatbot RAG · modelo: {datos["modelo"]} · repeticiones: {args.repeticiones}\n')
    print(informe(ejecuciones, args.repeticiones, casos))
    if args.detalle and (texto := detalle(ejecuciones)):
        print(f'\n{texto}')
    if args.json:
        print(json.dumps(datos, ensure_ascii=False, indent=2, default=str))
    print(f'\nDetalle guardado en {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}', file=sys.stderr)
    return 0 if all(e['correcto'] for e in ejecuciones) else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
