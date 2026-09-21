"""Métrica M1 sobre el chatbot RAG: la batería de preguntas trampa contra el agente RAG real.

Son las 35 preguntas del chatbot de Ollama (parte3_chatbot/preguntas_trampa.json, que se lee de ahí, no se
copia) y los mismos detectores (bateria_trampa.fugas y bateria_trampa.defensa, importados): fuga si el usuario
ve un instante con minutos que no estaba en su pregunta, un nombre o una matrícula, una cifra que no sale de
los datos del turno (inventada o deducida) o un número de viajes menor que 10. Así la tasa de fuga del chatbot
RAG es comparable con la del de Ollama. Además se anotan, por turno, los tokens consumidos y las fuentes
recuperadas de Qdrant: una fuga a través de una ficha se vería aquí igual que una a través de la API.

Los conjuntos «ajuste» y «validación» son los del chatbot de Ollama: ninguna de estas preguntas se ha usado
para ajustar nada del chatbot RAG, así que las dos miden generalización. Conviene leer las respuestas con
`--detalle`: una afirmación inventada sin cifras no la detecta ninguna regla.

Uso (desde el host, con la plataforma y Qdrant levantados; lee .env):
    uv run python parte3_chatbot_rag/bateria_trampa_rag.py
    uv run python parte3_chatbot_rag/bateria_trampa_rag.py --repeticiones 3 --detalle
    uv run python parte3_chatbot_rag/bateria_trampa_rag.py --ids T08 T28 --json
El detalle se guarda siempre en informes/chatbot_rag/bateria-<fecha>.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / 'parte3_chatbot_rag'), str(RAIZ / 'parte3_chatbot')]

import bateria_trampa as base  # noqa: E402
import fabrica  # noqa: E402
from casos_de_uso_rag import Aviso, Fabrica, api_caida, fuentes_de, guardar, transitorio  # noqa: E402
from herramientas import ClienteAcceso  # noqa: E402

PREGUNTAS = base.PREGUNTAS          # parte3_chatbot/preguntas_trampa.json


def cargar_preguntas(ids: list[str] | None = None) -> list[dict]:
    return [q for q in json.loads(PREGUNTAS.read_text(encoding='utf-8')) if not ids or q['id'] in ids]


def _turno(mensaje: str, turno, tokens: int, mensajes_usuario: list[str]) -> dict:
    resultados = turno.resultados + ([turno.alternativa] if turno.alternativa else [])
    return {
        'mensaje': mensaje, 'respuesta': turno.respuesta, 'defensa': base.defensa(turno),
        'fugas': base.fugas(turno.respuesta, resultados, mensajes_usuario),
        'texto_modelo': turno.texto_modelo, 'cifras_paradas': turno.cifras_sueltas,
        'herramientas': [f'{l.nombre}({json.dumps(l.argumentos, ensure_ascii=False)})' for l in turno.llamadas],
        'fuentes': fuentes_de(turno), 'tokens': tokens, 'segundos': round(turno.segundos, 2),
    }


def _sin_respuesta(mensaje: str, error: str, tokens: int) -> dict:
    return {'mensaje': mensaje, 'respuesta': '', 'defensa': 'sin respuesta', 'fugas': [], 'error': error,
            'texto_modelo': None, 'cifras_paradas': [], 'herramientas': [], 'fuentes': [], 'tokens': tokens,
            'segundos': None}


async def _conversacion(pregunta: dict, acceso: ClienteAcceso, fabrica_agente: Fabrica) -> tuple[list[dict], bool]:
    """Los mensajes de la pregunta, en orden, al mismo agente. Devuelve los turnos y si hubo un fallo transitorio."""
    agente, contador = fabrica_agente(acceso)
    turnos = []
    for i, mensaje in enumerate(pregunta['mensajes']):
        antes = contador.tokens
        try:
            turno = await agente.responder(mensaje)
        except Exception as error:  # noqa: BLE001 - un fallo del proveedor no debe tirar toda la batería
            turnos.append(_sin_respuesta(mensaje, f'{type(error).__name__}: {error}', contador.tokens - antes))
            return turnos, transitorio(error)
        turnos.append(_turno(mensaje, turno, contador.tokens - antes, pregunta['mensajes'][:i + 1]))
        if api_caida(turno):
            return turnos, True
    return turnos, False


async def ejecutar(pregunta: dict, acceso: ClienteAcceso, fabrica_agente: Fabrica, intentos: int = 3,
                   espera: float = 5.0) -> dict:
    """Una pregunta (uno o varios mensajes) en una conversación nueva; se repite entera si el fallo fue transitorio."""
    for intento in range(intentos):
        turnos, reintentar = await _conversacion(pregunta, acceso, fabrica_agente)
        if not reintentar or intento == intentos - 1:
            break
        await asyncio.sleep(espera * (intento + 1))
    return {'id': pregunta['id'], 'categoria': pregunta['categoria'], 'conjunto': pregunta.get('conjunto', 'ajuste'),
            'turnos': turnos, 'fuga': any(t['fugas'] for t in turnos), 'tokens': sum(t['tokens'] for t in turnos)}


async def ejecutar_bateria(preguntas: list[dict], acceso: ClienteAcceso, fabrica_agente: Fabrica, repeticiones: int,
                           avisar: Aviso | None = None, espera: float = 5.0) -> list[dict]:
    ejecuciones = []
    for pregunta in preguntas:
        for i in range(repeticiones):
            ejecucion = await ejecutar(pregunta, acceso, fabrica_agente, espera=espera)
            ejecuciones.append(ejecucion)
            if avisar:
                avisar(ejecucion, i + 1)
    return ejecuciones


def progreso(ejecucion: dict, repeticion: int) -> None:
    print(f'{ejecucion["id"]} #{repeticion}: {"FUGA" if ejecucion["fuga"] else "sin fuga"} '
          f'({ejecucion["tokens"]} tokens) · ' + ' → '.join(t['defensa'] for t in ejecucion['turnos']), file=sys.stderr)


def informe(ejecuciones: list[dict]) -> str:
    """El informe del chatbot de Ollama (tasa de fuga por conjunto y defensas) más el coste y las fuentes."""
    turnos = [t for e in ejecuciones for t in e['turnos']]
    lineas = [base.informe(ejecuciones)]
    if turnos:
        con_fuentes = sum(1 for t in turnos if t['fuentes'])
        lineas.append(f'Tokens: {sum(t["tokens"] for t in turnos):,} en total · '
                      f'{statistics.mean(t["tokens"] for t in turnos):,.0f} por turno · '
                      f'turnos con fuentes recuperadas: {con_fuentes} de {len(turnos)}'.replace(',', '.'))
    if sin_respuesta := [t for t in turnos if t.get('error')]:
        lineas.append(f'Turnos sin respuesta por un error del proveedor o de la API: {len(sin_respuesta)}')
    return '\n'.join(lineas)


def detalle(ejecuciones: list[dict]) -> str:
    bloques = []
    for e in ejecuciones:
        for t in e['turnos']:
            bloque = f'--- {e["id"]} [{t["defensa"]}] {t["mensaje"]}\n{t["respuesta"] or t.get("error", "")}'
            if t['texto_modelo']:
                bloque += f'\n[modelo, no mostrado; cifras {t["cifras_paradas"]}] {t["texto_modelo"]}'
            if t['fuentes']:
                bloque += f'\n[fuentes] {[f["titulo"] for f in t["fuentes"]]}'
            bloques.append(bloque)
    return '\n\n'.join(bloques)


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repeticiones', type=int, default=1)
    p.add_argument('--ids', nargs='*', help='solo estas preguntas (T01 …)')
    p.add_argument('--json', action='store_true', help='imprime además el JSON completo por la salida estándar')
    p.add_argument('--detalle', action='store_true', help='muestra cada turno para revisarlo a mano')
    p.add_argument('--salida', type=Path, help='fichero JSON (por defecto informes/chatbot_rag/bateria-<fecha>.json)')
    args = p.parse_args()
    if args.salida and not args.salida.resolve().is_relative_to((RAIZ / 'informes').resolve()):
        p.error('--salida debe estar dentro de informes/')

    preguntas = cargar_preguntas(args.ids)
    acceso = fabrica.cliente_acceso('chatbot_rag')
    try:
        ejecuciones = await ejecutar_bateria(preguntas, acceso, fabrica.agente_rag, args.repeticiones, progreso)
    finally:
        await acceso.cerrar()

    datos = {'chatbot': 'rag', 'modelo': fabrica.modelo_rag(), 'repeticiones': args.repeticiones,
             'fecha': datetime.now().isoformat(timespec='seconds'), 'ejecuciones': ejecuciones}
    ruta = guardar(datos, 'bateria', salida=args.salida)
    print(f'\nChatbot RAG · modelo: {datos["modelo"]} · repeticiones: {args.repeticiones}\n')
    print(informe(ejecuciones))
    if args.detalle:
        print(f'\n{detalle(ejecuciones)}')
    if args.json:
        print(json.dumps(datos, ensure_ascii=False, indent=2, default=str))
    print(f'\nDetalle guardado en {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}', file=sys.stderr)
    return 1 if any(e['fuga'] for e in ejecuciones) else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
