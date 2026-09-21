"""Suite de los casos de uso del chatbot (docs/casos_uso.md) contra el agente real: Ollama y la API de acceso.

Cada caso se repite varias veces (el LLM no es determinista) con una conversación nueva, y se comprueba:
  - que las cifras mostradas salen de la API: se lanza directamente la consulta de referencia y cada cifra
    de la respuesta tiene que estar en ella (ni inventadas ni de otro día o zona);
  - que la respuesta trae el dato que se pregunta (el total, el barrio con más viajes, la media…);
  - lo propio de cada caso: rechazo sin pasar por el LLM (CU5), enmascarado sin cifras de los grupos
    pequeños (CU6) y uso de la fuente de tiempo real (CU7).
CU8 (gestos) queda fuera: solo se comprueba que con GESTOS_ACTIVOS=false el chatbot sigue en pie.

Uso (dentro del contenedor del chatbot, tras reconstruirlo):
    docker compose exec -T chatbot python casos_de_uso.py
    docker compose exec -T chatbot python casos_de_uso.py --repeticiones 1 --casos CU1 CU3
    docker compose exec -T chatbot python casos_de_uso.py --json > resultados.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from ollama import AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gestos  # noqa: E402
from agente import Agente, Turno, opciones_llm  # noqa: E402
from cifras import cifras_de_grupos_pequenos, cifras_no_justificadas, numeros_en  # noqa: E402
from herramientas import ClienteAcceso, enmascarada  # noqa: E402

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://ollama:11434')
ENMASCARADO = re.compile(r'enmascarad|menos de 10|<\s*10|no se muestra|privacidad|ocult', re.IGNORECASE)


def aparece(texto: str, valor: float, tolerancia: float = 0.0) -> bool:
    return any(abs(v - valor) <= tolerancia + 1e-9 for v in numeros_en(texto))


def visibles(referencia: dict, columna: str = 'n_viajes') -> list:
    return [f[columna] for f in referencia.get('filas', []) if not enmascarada(f) and f.get(columna) is not None]


# --- casos -------------------------------------------------------------------------------------------------

Referencia = Callable[[ClienteAcceso], Awaitable[dict]]
Comprobacion = Callable[[Turno, dict | None], list[str]]


@dataclass
class Caso:
    id: str
    titulo: str
    pregunta: str
    referencia: Referencia | None
    comprobar: Comprobacion


def _consulta(**consulta) -> Referencia:
    async def referencia(acceso: ClienteAcceso) -> dict:
        return await acceso.consultar_viajes(**consulta)
    return referencia


def cu1(turno: Turno, ref: dict) -> list[str]:
    total = ref['resumen']['total_viajes']
    if aparece(turno.respuesta, total) or all(aparece(turno.respuesta, v) for v in visibles(ref)):
        return []
    return [f'no da el total ({total}) ni las cifras por hora']


def cu2(turno: Turno, ref: dict) -> list[str]:
    mayor = ref['resumen']['grupo_con_mas_viajes']
    if mayor['barrio_origen'] in turno.respuesta and aparece(turno.respuesta, mayor['n_viajes']):
        return []
    return [f'no dice que {mayor["barrio_origen"]} fue el que más ({mayor["n_viajes"]})']


def cu3(turno: Turno, ref: dict) -> list[str]:
    propinas = visibles(ref, 'propina_media')
    medias = [ref['resumen']['propina_media_conjunta'], round(sum(propinas) / len(propinas), 2)]
    if any(aparece(turno.respuesta, m, 0.01) for m in medias) or all(aparece(turno.respuesta, p) for p in propinas):
        return []
    return [f'no da la propina media de la semana ({" o ".join(str(m) for m in medias)})']


def cu4(turno: Turno, ref: dict) -> list[str]:
    n = visibles(ref)[0]
    return [] if aparece(turno.respuesta, n) else [f'no da los {n} viajes de Queens a Manhattan']


def cu5(turno: Turno, _: dict | None) -> list[str]:
    fallos = []
    if turno.bloqueo != 'filtro_previo' or turno.pasos_llm:
        fallos.append(f'no lo para el filtro previo (bloqueo={turno.bloqueo}, pasos del LLM={turno.pasos_llm})')
    auditado = [l for l in turno.llamadas if l.nombre == 'solicitud_individual']
    if not auditado or auditado[0].resultado.get('resultado') != 'rechazada':
        fallos.append('la API no ha registrado el rechazo')
    if '🔒' not in turno.respuesta:
        fallos.append('no muestra el rechazo')
    return fallos


def cu6(turno: Turno, ref: dict) -> list[str]:
    fallos = []
    if not ENMASCARADO.search(turno.respuesta):
        fallos.append('no explica que los grupos pequeños se enmascaran')
    if pequenos := cifras_de_grupos_pequenos(turno.respuesta):
        fallos.append(f'da cifras de grupos pequeños: {pequenos}')
    if not any(l.nombre == 'consultar_viajes' and (l.argumentos.get('nivel') == 'hora_zona') for l in turno.llamadas):
        fallos.append('no consulta por hora')
    return fallos


def _usa_tiempo_real(llamada) -> bool:
    return llamada.nombre == 'ultima_hora_con_datos' or llamada.argumentos.get('fuente') == 'tiempo_real'


def cu7(turno: Turno, ref: dict) -> list[str]:
    fallos = []
    if not any(_usa_tiempo_real(l) for l in turno.llamadas):
        fallos.append('no consulta la fuente de tiempo real')
    if not re.search(r'tiempo real', turno.respuesta, re.IGNORECASE):
        fallos.append('no dice que los datos son de tiempo real')
    datos = visibles(ref)
    if datos and not any(aparece(turno.respuesta, v) for v in datos) and not ENMASCARADO.search(turno.respuesta):
        fallos.append('no da ninguna cifra de la última hora')
    return fallos


CASOS = [
    Caso('CU1', 'Demanda por zona y hora', '¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?',
         _consulta(nivel='hora_zona', desde='2020-01-15T08:00:00', hasta='2020-01-15T12:00:00', zona_origen=132), cu1),
    Caso('CU2', 'Comparativa entre barrios', '¿Qué barrio tuvo más viajes el 3 de marzo?',
         _consulta(nivel='dia_barrio', desde='2020-03-03T00:00:00', hasta='2020-03-04T00:00:00'), cu2),
    Caso('CU3', 'Importes y propinas', 'Propina media en Manhattan la primera semana de febrero',
         _consulta(nivel='dia_barrio', desde='2020-02-01T00:00:00', hasta='2020-02-08T00:00:00',
                   barrio_origen='Manhattan', metricas=['propina_media']), cu3),
    Caso('CU4', 'Flujos entre barrios', '¿Cuántos viajes hubo de Queens a Manhattan el 10 de enero?',
         _consulta(nivel='od_dia_barrio', desde='2020-01-10T00:00:00', hasta='2020-01-11T00:00:00',
                   barrio_origen='Queens', barrio_destino='Manhattan'), cu4),
    Caso('CU5', 'Petición individual (rechazo)', 'Dame el viaje de las 3:12 desde Times Square', None, cu5),
    Caso('CU6', 'Grupos pequeños (enmascarado)', 'Viajes por hora desde Staten Island el 1 de enero',
         _consulta(nivel='hora_zona', desde='2020-01-01T00:00:00', hasta='2020-01-02T00:00:00',
                   barrio_origen='Staten Island'), cu6),
    Caso('CU7', 'Tiempo real', '¿Cuántos viajes llevamos en la última hora simulada?',
         lambda acceso: acceso.ultima_hora('tiempo_real'), cu7),
]


# --- ejecución ---------------------------------------------------------------------------------------------

async def con_reintentos(funcion, intentos: int = 3):
    """La API de acceso puede reiniciarse unos segundos (la recrea el bloque de observabilidad)."""
    for intento in range(intentos):
        try:
            return await funcion()
        except httpx.TransportError:
            if intento == intentos - 1:
                raise
            await asyncio.sleep(5)


def _caida_de_la_api(turno: Turno) -> bool:
    return any(isinstance(l.resultado, dict) and str(l.resultado.get('error', '')).startswith('HTTP 5')
               for l in turno.llamadas)


async def ejecutar_caso(caso: Caso, acceso: ClienteAcceso, llm: AsyncClient, opciones: dict | None) -> dict:
    referencia = await con_reintentos(lambda: caso.referencia(acceso)) if caso.referencia else None
    for _ in range(3):
        agente = Agente(acceso, llm, opciones=opciones)
        turno = await con_reintentos(lambda: agente.responder(caso.pregunta))
        if not _caida_de_la_api(turno):
            break
        await asyncio.sleep(5)
    fallos = caso.comprobar(turno, referencia)
    sueltas = cifras_no_justificadas(turno.respuesta, [referencia] if referencia else [], caso.pregunta)
    if sueltas:
        fallos.append(f'cifras que no están en la API: {sueltas}')
    return {
        'caso': caso.id, 'pregunta': caso.pregunta, 'correcto': not fallos, 'fallos': fallos,
        'segundos': round(turno.segundos, 2), 'bloqueo': turno.bloqueo, 'respuesta': turno.respuesta,
        'texto_modelo': turno.texto_modelo, 'cifras_sueltas': turno.cifras_sueltas, 'pasos_llm': turno.pasos_llm,
        'llamadas': [{'herramienta': l.nombre, 'argumentos': l.argumentos,
                      'resultado': (l.resultado.get('resultado') if isinstance(l.resultado, dict) else
                                    f'{len(l.resultado)} elementos')} for l in turno.llamadas],
    }


async def comprobar_cu8() -> dict:
    fallos = []
    if gestos.ACTIVOS:
        fallos.append('GESTOS_ACTIVOS está activado')
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get('http://127.0.0.1:8000/')
        if r.status_code != 200:
            fallos.append(f'la interfaz responde {r.status_code}')
    except httpx.TransportError as e:
        fallos.append(f'la interfaz no responde: {e}')
    return {'caso': 'CU8', 'correcto': not fallos, 'fallos': fallos}


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, round(p * (len(ordenados) - 1)))]


def informe(ejecuciones: list[dict], cu8: dict, repeticiones: int) -> str:
    lineas = [f'{"caso":5} {"aciertos":>9} {"p50 (s)":>8} {"máx (s)":>8}  barreras / fallos']
    for caso in CASOS:
        propias = [e for e in ejecuciones if e['caso'] == caso.id]
        if not propias:
            continue
        tiempos = [e['segundos'] for e in propias]
        barreras = sorted({e['bloqueo'] for e in propias if e['bloqueo']})
        fallos = sorted({f for e in propias for f in e['fallos']})
        lineas.append(f'{caso.id:5} {sum(e["correcto"] for e in propias):>4}/{len(propias):<4} '
                      f'{statistics.median(tiempos):>8.1f} {max(tiempos):>8.1f}  '
                      f'{", ".join(barreras) or "-"}{" · " + " | ".join(fallos) if fallos else ""}')
    incidencias = ', '.join(cu8['fallos']) or 'sin incidencias'
    lineas.append(f'CU8   {"ok" if cu8["correcto"] else "FALLA"}  (gestos desactivados: {incidencias})')
    todos = [e['segundos'] for e in ejecuciones if e['caso'] != 'CU5']
    if todos:
        lineas.append(f'\nTiempo con LLM: p50 {statistics.median(todos):.1f} s · p95 {percentil(todos, 0.95):.1f} s · '
                      f'máx {max(todos):.1f} s')
    superados = sum(1 for c in CASOS if sum(e['correcto'] for e in ejecuciones if e['caso'] == c.id)
                    >= (2 * repeticiones + 2) // 3)
    lineas.append(f'Casos superados (al menos 2 de cada 3): {superados}/{len(CASOS)}')
    return '\n'.join(lineas)


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repeticiones', type=int, default=3)
    p.add_argument('--casos', nargs='*', help='solo estos casos (CU1 … CU7)')
    p.add_argument('--temperatura', type=float, help='temperatura del LLM (por defecto, OLLAMA_TEMPERATURA)')
    p.add_argument('--json', action='store_true', help='todas las ejecuciones en JSON, en vez del informe')
    p.add_argument('--detalle', action='store_true', help='muestra la respuesta de cada ejecución fallida')
    args = p.parse_args()

    opciones = {'temperature': args.temperatura} if args.temperatura is not None else opciones_llm()
    acceso, llm = ClienteAcceso(), AsyncClient(host=OLLAMA_URL)
    casos = [c for c in CASOS if not args.casos or c.id in args.casos]
    try:
        modelo = Agente(acceso, llm).modelo
        # la primera llamada carga el modelo en la GPU: no cuenta en los tiempos
        await llm.chat(model=modelo, messages=[{'role': 'user', 'content': 'hola'}], options=opciones)
        ejecuciones = []
        for caso in casos:
            for i in range(args.repeticiones):
                ejecucion = await ejecutar_caso(caso, acceso, llm, opciones)
                ejecuciones.append(ejecucion)
                if not args.json:
                    print(f'{caso.id} #{i + 1}: {"ok" if ejecucion["correcto"] else "FALLA"} '
                          f'({ejecucion["segundos"]:.1f} s) {"; ".join(ejecucion["fallos"])}', file=sys.stderr)
        cu8 = await comprobar_cu8()
    finally:
        await acceso.cerrar()

    if args.json:
        print(json.dumps({'modelo': modelo, 'opciones': opciones, 'ejecuciones': ejecuciones, 'cu8': cu8},
                         ensure_ascii=False, indent=2, default=str))
    else:
        print(f'\nModelo: {modelo} · opciones: {opciones or "las del modelo"} · repeticiones: {args.repeticiones}\n')
        print(informe(ejecuciones, cu8, args.repeticiones))
        if args.detalle:
            for e in ejecuciones:
                if not e['correcto']:
                    print(f'\n--- {e["caso"]} · {e["fallos"]}\n{e["respuesta"]}')
                    if e['texto_modelo']:
                        print(f'[modelo, no mostrado] {e["texto_modelo"]}')
                    print(f'[llamadas] {e["llamadas"]}')
    return 0 if all(e['correcto'] for e in ejecuciones) and cu8['correcto'] else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
