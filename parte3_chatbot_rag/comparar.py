"""Compara los dos chatbots sobre la misma suite de casos de uso y la misma batería trampa: el de Ollama (LLM
local, parte3_chatbot) y el RAG (Helmcode + Qdrant, parte3_chatbot_rag).

Saca la tabla aciertos / p50 / p95 / tokens / fugas que va a docs/casos_uso.md y docs/metricas_calidad.md, y
guarda el detalle de todas las ejecuciones en informes/chatbot_rag/comparativa-<fecha>.json. Los dos agentes
usan la misma API de acceso, cada uno con su clave (`chatbot` y `chatbot_rag`), así que la auditoría los
distingue. Las ejecuciones van en serie: el proveedor limita las peticiones por minuto y la GPU es una.

Uso (desde el host, con la plataforma, Ollama y Qdrant levantados; lee .env):
    uv run python parte3_chatbot_rag/comparar.py                          # casos ×3 y batería ×3 de los dos
    uv run python parte3_chatbot_rag/comparar.py --solo casos --repeticiones 1
    uv run python parte3_chatbot_rag/comparar.py --agentes rag            # solo el chatbot RAG
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / 'parte3_chatbot_rag'), str(RAIZ / 'parte3_chatbot')]

import bateria_trampa_rag as bateria  # noqa: E402
import casos_de_uso_rag as casos  # noqa: E402
import fabrica  # noqa: E402
from agente import MODELO as MODELO_OLLAMA  # noqa: E402
from agente import opciones_llm  # noqa: E402
from casos_de_uso import CASOS, percentil  # noqa: E402

# clave -> (nombre en la tabla, cliente de la API de acceso, modelo, fábrica del agente)
AGENTES = {
    'ollama': ('Ollama (local)', 'chatbot', lambda: MODELO_OLLAMA, fabrica.agente_ollama),
    'rag': ('RAG (Helmcode)', 'chatbot_rag', fabrica.modelo_rag, fabrica.agente_rag),
}


def resumen(nombre: str, modelo: str, ejecuciones_casos: list[dict], ejecuciones_bateria: list[dict],
            repeticiones: int, lista_casos=CASOS) -> dict:
    tiempos = casos.tiempos_con_llm(ejecuciones_casos)
    turnos = [t for e in ejecuciones_bateria for t in e['turnos']]
    return {
        'agente': nombre, 'modelo': modelo,
        'ejecuciones_correctas': sum(e['correcto'] for e in ejecuciones_casos), 'ejecuciones': len(ejecuciones_casos),
        'casos_superados': casos.casos_superados(ejecuciones_casos, repeticiones, lista_casos) if ejecuciones_casos else None,
        'casos': len(lista_casos),
        'p50': round(statistics.median(tiempos), 2) if tiempos else None,
        'p95': round(percentil(tiempos, 0.95), 2) if tiempos else None,
        'tokens_por_ejecucion': round(statistics.mean(e['tokens'] for e in ejecuciones_casos)) if ejecuciones_casos else None,
        'fugas': sum(e['fuga'] for e in ejecuciones_bateria), 'bateria': len(ejecuciones_bateria),
        'tokens_por_turno_bateria': round(statistics.mean(t['tokens'] for t in turnos)) if turnos else None,
    }


def _numero(valor, decimales: int = 0, unidad: str = '') -> str:
    if valor is None:
        return '—'
    texto = f'{valor:,.{decimales}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'{texto}{unidad}'


def tabla(resumenes: list[dict]) -> str:
    """Tabla en Markdown, lista para pegar en la documentación."""
    cabecera = ['Chatbot', 'Modelo', 'Ejecuciones correctas', 'Casos superados', 'p50', 'p95',
                'Tokens por pregunta', 'Fugas en la batería', 'Tokens por turno (batería)']
    filas = [[
        r['agente'], f'`{r["modelo"]}`',
        f'{r["ejecuciones_correctas"]}/{r["ejecuciones"]}' if r['ejecuciones'] else '—',
        f'{r["casos_superados"]}/{r["casos"]}' if r['casos_superados'] is not None else '—',
        _numero(r['p50'], 1, ' s'), _numero(r['p95'], 1, ' s'), _numero(r['tokens_por_ejecucion']),
        f'{r["fugas"]}/{r["bateria"]}' if r['bateria'] else '—', _numero(r['tokens_por_turno_bateria']),
    ] for r in resumenes]
    lineas = ['| ' + ' | '.join(cabecera) + ' |', '|' + '---|' * len(cabecera)]
    lineas += ['| ' + ' | '.join(fila) + ' |' for fila in filas]
    return '\n'.join(lineas)


async def calentar_ollama(acceso) -> None:
    """La primera llamada carga el modelo en la GPU (unos 40 s): no debe contar en los tiempos."""
    _, contador = fabrica.agente_ollama(acceso)
    await contador.chat(model=MODELO_OLLAMA, messages=[{'role': 'user', 'content': 'hola'}], options=opciones_llm())


async def evaluar(clave: str, lista_casos, preguntas: list[dict], repeticiones: int, repeticiones_bateria: int,
                  que: set[str]) -> dict:
    nombre, cliente, modelo, fabrica_agente = AGENTES[clave]
    acceso = fabrica.cliente_acceso(cliente)
    ejecuciones_casos: list[dict] = []
    ejecuciones_bateria: list[dict] = []
    try:
        if clave == 'ollama':
            await calentar_ollama(acceso)
        if 'casos' in que:
            print(f'\n== {nombre} · casos de uso ==', file=sys.stderr)
            ejecuciones_casos = await casos.ejecutar_suite(lista_casos, acceso, fabrica_agente, repeticiones,
                                                           casos.progreso)
        if 'bateria' in que:
            print(f'\n== {nombre} · batería trampa ==', file=sys.stderr)
            ejecuciones_bateria = await bateria.ejecutar_bateria(preguntas, acceso, fabrica_agente,
                                                                 repeticiones_bateria, bateria.progreso)
    finally:
        await acceso.cerrar()
    return {'nombre': nombre, 'modelo': modelo(), 'casos': ejecuciones_casos, 'bateria': ejecuciones_bateria,
            'resumen': resumen(nombre, modelo(), ejecuciones_casos, ejecuciones_bateria, repeticiones, lista_casos)}


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--agentes', nargs='*', choices=sorted(AGENTES), default=['ollama', 'rag'])
    p.add_argument('--solo', choices=['casos', 'bateria'], help='solo la suite de casos o solo la batería')
    p.add_argument('--repeticiones', type=int, default=3, help='repeticiones de cada caso de uso')
    p.add_argument('--repeticiones-bateria', type=int, default=3, help='repeticiones de cada pregunta trampa')
    p.add_argument('--casos', nargs='*', help='solo estos casos (CU1 … CU7)')
    p.add_argument('--ids', nargs='*', help='solo estas preguntas trampa (T01 …)')
    p.add_argument('--salida', type=Path, help='JSON (por defecto informes/chatbot_rag/comparativa-<fecha>.json)')
    args = p.parse_args()
    if args.salida and not args.salida.resolve().is_relative_to((RAIZ / 'informes').resolve()):
        p.error('--salida debe estar dentro de informes/')

    que = {args.solo} if args.solo else {'casos', 'bateria'}
    lista_casos = [c for c in CASOS if not args.casos or c.id in args.casos]
    preguntas = bateria.cargar_preguntas(args.ids)
    resultados = {}
    for clave in args.agentes:
        resultados[clave] = await evaluar(clave, lista_casos, preguntas, args.repeticiones, args.repeticiones_bateria, que)

    datos = {'fecha': datetime.now().isoformat(timespec='seconds'), 'repeticiones': args.repeticiones,
             'repeticiones_bateria': args.repeticiones_bateria, 'agentes': resultados}
    ruta = casos.guardar(datos, 'comparativa', salida=args.salida)
    partes = [f'suite de {len(lista_casos)} casos × {args.repeticiones}' if 'casos' in que else '',
              f'batería de {len(preguntas)} preguntas × {args.repeticiones_bateria}' if 'bateria' in que else '']
    print(f'\nLa misma {" y la misma ".join(p for p in partes if p)} para cada chatbot:\n')
    print(tabla([r['resumen'] for r in resultados.values()]))
    print(f'\nDetalle guardado en {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
