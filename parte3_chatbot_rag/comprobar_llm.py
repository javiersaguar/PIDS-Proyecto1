"""Comprueba el proveedor LLM de punta a punta: modelos, chat, llamada a herramienta, embeddings, rerank y veto.

Uso desde la raíz del repositorio (lee LLM_API_KEY del entorno o, si falta, de .env):
    uv run python parte3_chatbot_rag/comprobar_llm.py [--modelo qwen3.6] [--razonamiento none]
Dentro de Docker (el entorno lo pone docker-compose):
    make rag-comprobar ARGS='--modelo qwen3.6'

Sale con código 1 si alguna comprobación falla. No imprime nunca la clave.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RAIZ / 'parte3_chatbot'))

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage  # noqa: E402

import llm as L  # noqa: E402

PREGUNTA = '¿Cuántos viajes salieron de JFK el 15 de enero de 2020 entre las 8 y las 12?'
RESULTADO_FALSO = {
    'resultado': 'permitida',
    'consulta': {'nivel': 'hora_zona', 'zona_origen': 132, 'desde': '2020-01-15T08:00:00', 'hasta': '2020-01-15T12:00:00'},
    'filas': [{'hora': '2020-01-15T08:00', 'zona_origen_nombre': 'JFK Airport', 'n_viajes': 144},
              {'hora': '2020-01-15T09:00', 'zona_origen_nombre': 'JFK Airport', 'n_viajes': 168},
              {'hora': '2020-01-15T10:00', 'zona_origen_nombre': 'JFK Airport', 'n_viajes': 197},
              {'hora': '2020-01-15T11:00', 'zona_origen_nombre': 'JFK Airport', 'n_viajes': 143}],
    'resumen': {'grupos': 4, 'grupos_visibles': 4, 'grupos_enmascarados': 0, 'total_viajes': 652},
}


def cargar_env(ruta: Path = RAIZ / '.env') -> None:
    """Completa el entorno con las variables LLM_* de .env que falten (fuera de Docker)."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        if '=' in linea and not linea.lstrip().startswith('#'):
            clave, valor = linea.split('=', 1)
            if clave.startswith('LLM_') and valor and not os.environ.get(clave):
                os.environ[clave] = valor


class Informe:
    def __init__(self) -> None:
        self.fallos = 0

    def ok(self, texto: str) -> None:
        print(f'  ✔ {texto}')

    def mal(self, texto: str) -> None:
        self.fallos += 1
        print(f'  ✘ {texto}')

    def comprobar(self, condicion: bool, texto: str) -> bool:
        (self.ok if condicion else self.mal)(texto)
        return condicion


async def paso_modelos(inf: Informe, modelo: str, embeddings: str) -> None:
    print('1. Modelos disponibles para la clave')
    ids = await L.modelos_disponibles()
    permitidos = [m for m in ids if L.modelo_permitido(m)]
    vetados = [m for m in ids if not L.modelo_permitido(m)]
    inf.ok(f'{len(ids)} modelos; permitidos (UE): {", ".join(permitidos)}')
    if vetados:
        inf.ok(f'vetados por E3 (salen de la UE o se pagan aparte): {", ".join(vetados)}')
    inf.comprobar(modelo in ids, f'el modelo de chat {modelo!r} está disponible')
    inf.comprobar(embeddings in ids, f'el modelo de embeddings {embeddings!r} está disponible')


async def paso_chat(inf: Informe, modelo: str, razonamiento: str | None) -> None:
    print('2. Chat')
    chat = L.obtener_llm(modelo=modelo, razonamiento=razonamiento)
    inicio = time.monotonic()
    respuesta = await chat.ainvoke([HumanMessage('Responde solo con la palabra: listo')])
    segundos = time.monotonic() - inicio
    contenido = str(respuesta.content)
    inf.comprobar('listo' in contenido.lower(), f'responde «{contenido.strip()[:40]}» en {segundos:.1f} s')
    inf.comprobar('<think>' not in contenido, 'el razonamiento no se cuela en la respuesta')
    tokens = L.tokens_de(respuesta)
    inf.comprobar(tokens['total'] > 0, f'tokens: {tokens}')
    razon = L.razonamiento_de(respuesta)
    inf.ok(f'razonamiento aparte: {"sí, " + str(len(razon)) + " caracteres" if razon else "no (o desactivado)"}')


async def paso_herramienta(inf: Informe, modelo: str, razonamiento: str | None) -> None:
    print('3. Llamada a herramienta con el esquema real de consultar_viajes')
    from herramientas import ESQUEMAS
    chat = L.obtener_llm(modelo=modelo, razonamiento=razonamiento).bind_tools(ESQUEMAS)
    mensajes = [SystemMessage('Eres el asistente de datos de una empresa de taxis de Nueva York (2020). '
                              'Usa las herramientas para obtener los datos; nunca inventes cifras.'),
                HumanMessage(PREGUNTA)]
    inicio = time.monotonic()
    respuesta = await chat.ainvoke(mensajes)
    llamadas = respuesta.tool_calls or []
    if not inf.comprobar(bool(llamadas), f'el modelo llama a una herramienta ({time.monotonic() - inicio:.1f} s)'):
        print('    respuesta:', str(respuesta.content)[:200])
        return
    llamada = llamadas[0]
    args = llamada['args']
    inf.comprobar(llamada['name'] == 'consultar_viajes', f'herramienta: {llamada["name"]}')
    inf.comprobar(args.get('nivel') == 'hora_zona', f'nivel: {args.get("nivel")}')
    inf.comprobar(str(args.get('desde', '')).startswith('2020-01-15T08'), f'desde: {args.get("desde")}')
    inf.comprobar(str(args.get('hasta', '')).startswith('2020-01-15T12'), f'hasta: {args.get("hasta")}')
    inf.ok(f'zona_origen: {args.get("zona_origen")!r}')
    mensajes += [respuesta, ToolMessage(content=json.dumps(RESULTADO_FALSO, ensure_ascii=False),
                                        tool_call_id=llamada['id'])]
    inicio = time.monotonic()
    final = await chat.ainvoke(mensajes)
    texto = str(final.content)
    inf.comprobar('652' in texto, f'usa la cifra del resumen ({time.monotonic() - inicio:.1f} s): «{texto.strip()[:120]}»')


async def paso_embeddings(inf: Informe, modelo: str) -> None:
    print('4. Embeddings')
    emb = L.obtener_embeddings(modelo=modelo)
    inicio = time.monotonic()
    vectores = await emb.aembed_documents(['viajes por hora desde el aeropuerto JFK', 'propina media en Manhattan'])
    consulta = await emb.aembed_query('aeropuerto')
    inf.comprobar(len(vectores) == 2 and all(len(v) == L.DIMENSION_EMBEDDINGS for v in vectores),
                  f'{len(vectores)} documentos de {len(vectores[0])} dimensiones en {time.monotonic() - inicio:.1f} s')
    inf.comprobar(len(consulta) == L.DIMENSION_EMBEDDINGS, 'la consulta tiene la misma dimensión')


async def paso_rerank(inf: Informe) -> None:
    print('5. Rerank')
    docs = ['JFK Airport, Queens', 'Times Sq/Theatre District, Manhattan', 'LaGuardia Airport, Queens']
    orden = await L.reordenar('aeropuerto', docs, top_n=2)
    inf.comprobar(len(orden) == 2 and all(i in (0, 2) for i, _ in orden),
                  f'los dos primeros son aeropuertos: {[docs[i] for i, _ in orden]}')


def paso_veto(inf: Informe) -> None:
    print('6. Lista blanca')
    for modelo in ('claude-sonnet-5', 'gpt-5.6-sol', 'gemini-3.6-flash'):
        try:
            L.obtener_llm(modelo=modelo)
            inf.mal(f'{modelo} debería estar vetado')
        except L.ModeloNoPermitido:
            inf.ok(f'{modelo} vetado')


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modelo', default=None, help='modelo de chat (por defecto LLM_MODELO)')
    p.add_argument('--embeddings', default=None, help='modelo de embeddings (por defecto LLM_MODELO_EMBEDDINGS)')
    p.add_argument('--razonamiento', default=None, choices=L.NIVELES_RAZONAMIENTO,
                   help='reasoning_effort; none lo apaga en qwen3.6 y gemma4')
    p.add_argument('--sin-rerank', action='store_true')
    args = p.parse_args()
    cargar_env()
    modelo = args.modelo or os.environ.get('LLM_MODELO', L.MODELO_POR_DEFECTO)
    embeddings = args.embeddings or os.environ.get('LLM_MODELO_EMBEDDINGS', L.EMBEDDINGS_POR_DEFECTO)
    print(f'Proveedor: {L.base_url()} · chat: {modelo} · embeddings: {embeddings}')
    inf = Informe()
    try:
        L.clave()
    except L.FaltaClave as e:
        inf.mal(str(e))
        return 1
    pasos = [paso_modelos(inf, modelo, embeddings), paso_chat(inf, modelo, args.razonamiento),
             paso_herramienta(inf, modelo, args.razonamiento), paso_embeddings(inf, embeddings)]
    if not args.sin_rerank:
        pasos.append(paso_rerank(inf))
    for paso in pasos:
        try:
            await paso
        except Exception as e:  # noqa: BLE001 - se informa y se sigue con el resto
            inf.mal(f'{type(e).__name__}: {str(e)[:200]}')
    paso_veto(inf)
    print('Todo correcto' if not inf.fallos else f'{inf.fallos} comprobaciones han fallado')
    return 1 if inf.fallos else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
