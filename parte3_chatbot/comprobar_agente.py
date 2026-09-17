"""Prueba el agente sin interfaz: una pregunta, las herramientas reales y la API de acceso.

Sirve para comprobar que el LLM llama bien a las herramientas y que la API responde, sin abrir
Chainlit en el navegador. Útil también para probar otro modelo antes de cambiarlo en .env.

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

from herramientas import (  # noqa: E402
    ESQUEMAS, INSTRUCCION_RECHAZO, ClienteAcceso, hay_datos, parece_individual, tiene_cifras)
from prompts import SISTEMA  # noqa: E402

PREGUNTA = '¿Cuántos viajes salieron de cada barrio el 1 de enero de 2020?'
MAX_PASOS = 4


async def main() -> int:
    pregunta = ' '.join(sys.argv[1:]) or PREGUNTA
    acceso = ClienteAcceso()
    llm = AsyncClient(host=os.environ.get('OLLAMA_URL', 'http://ollama:11434'))
    modelo = os.environ.get('OLLAMA_MODELO', 'llama3.1:8b')
    print(f'Modelo: {modelo}\nPregunta: {pregunta}')

    if parece_individual(pregunta):
        print('\nFiltro previo: parece una petición de datos individuales (no llega al LLM)')
        print(json.dumps(await acceso.solicitud_individual(pregunta), ensure_ascii=False, indent=2))
        await acceso.cerrar()
        return 0

    mensajes: list = [{'role': 'system', 'content': SISTEMA}, {'role': 'user', 'content': pregunta}]
    datos = False
    for paso in range(MAX_PASOS):
        respuesta = await llm.chat(model=modelo, messages=mensajes, tools=ESQUEMAS)
        mensajes.append(respuesta.message)
        llamadas = respuesta.message.tool_calls or []
        if not llamadas:
            contenido = respuesta.message.content or ''
            print(f'\nRespuesta:\n{contenido}')
            if not datos and tiene_cifras(contenido):
                print('\n*** BARRERA: cifras sin datos detrás. En la interfaz esta respuesta se sustituye '
                      'por el rechazo con su alternativa. ***')
                await acceso.cerrar()
                return 1
            await acceso.cerrar()
            return 0
        for llamada in llamadas:
            nombre, argumentos = llamada.function.name, dict(llamada.function.arguments or {})
            print(f'\n[paso {paso + 1}] herramienta: {nombre}({json.dumps(argumentos, ensure_ascii=False)})')
            resultado = await acceso.ejecutar(nombre, argumentos)
            datos = datos or hay_datos(resultado)
            print(f'    respuesta: {json.dumps(resultado, ensure_ascii=False, default=str)[:600]}')
            aviso = INSTRUCCION_RECHAZO if isinstance(resultado, dict) and \
                resultado.get('resultado') == 'rechazada' else ''
            mensajes.append({'role': 'tool', 'tool_name': nombre,
                             'content': json.dumps(resultado, ensure_ascii=False, default=str)[:12000] + aviso})
    print('\nEl modelo no ha terminado en %d pasos' % MAX_PASOS)
    await acceso.cerrar()
    return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
