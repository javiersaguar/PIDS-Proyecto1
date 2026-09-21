"""Prueba el agente sin interfaz: una pregunta, las herramientas reales y la API de acceso.

Sirve para comprobar que el LLM llama bien a las herramientas y que la API responde, sin abrir
Chainlit en el navegador. Útil también para probar otro modelo antes de cambiarlo en .env.
Ejecuta exactamente el mismo agente que la interfaz (agente.py).

Uso (dentro del contenedor del chatbot):
    docker compose exec chatbot python comprobar_agente.py
    docker compose exec chatbot python comprobar_agente.py "¿Qué barrio tuvo más viajes el 1 de enero?"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from ollama import AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agente import Agente  # noqa: E402
from herramientas import ClienteAcceso  # noqa: E402

PREGUNTA = '¿Cuántos viajes salieron de cada barrio el 1 de enero de 2020?'


async def main() -> int:
    pregunta = ' '.join(sys.argv[1:]) or PREGUNTA
    acceso = ClienteAcceso()
    agente = Agente(acceso, AsyncClient(host=os.environ.get('OLLAMA_URL', 'http://ollama:11434')))
    print(f'Modelo: {agente.modelo}\nPregunta: {pregunta}')
    try:
        turno = await agente.responder(pregunta)
    finally:
        await acceso.cerrar()

    if turno.bloqueo == 'filtro_previo':
        print('\nFiltro previo: parece una petición de datos individuales (no llega al LLM)')
    for paso, llamada in enumerate(turno.llamadas, 1):
        print(f'\n[paso {paso}] herramienta: {llamada.nombre}({json.dumps(llamada.argumentos, ensure_ascii=False)})')
        print(f'    respuesta: {json.dumps(llamada.resultado, ensure_ascii=False, default=str)[:600]}')
    if turno.texto_modelo:
        print(f'\nRespuesta del modelo (no se muestra):\n{turno.texto_modelo}')
    print(f'\nRespuesta ({turno.segundos:.1f} s):\n{turno.respuesta}')
    if turno.bloqueo in ('sin_datos', 'cifras_no_verificadas'):
        detalle = f': {", ".join(turno.cifras_sueltas)}' if turno.cifras_sueltas else ''
        print(f'\n*** BARRERA ({turno.bloqueo}{detalle}): la respuesta del modelo se ha sustituido. ***')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
