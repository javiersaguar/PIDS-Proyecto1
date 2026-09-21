"""Instrucciones del agente RAG.

Son las del chatbot de Ollama (parte3_chatbot/prompts.py), con la misma sección de privacidad, más las
reglas sobre el contexto recuperado: qué es, para qué sirve y cómo citar sus fuentes. El bloque de contexto
se reconstruye en cada turno (`formatear_contexto`) y va al final del mensaje de sistema, no en el
historial: así no se acumula en cada pregunta.
"""
from __future__ import annotations

import os
from typing import Any

from prompts import BIENVENIDA, SISTEMA

# Cada fragmento recuperado se recorta a este tamaño: el contexto sirve para orientar, no para volcar documentos
MAX_CARACTERES_DOCUMENTO = int(os.environ.get('RAG_MAX_CARACTERES_DOCUMENTO', '2000'))
ENCABEZADO_CONTEXTO = '# Contexto recuperado para la pregunta actual'
SIN_CONTEXTO = '(no se ha recuperado ningún fragmento para esta pregunta)'

SISTEMA_RAG = SISTEMA + """
Contexto recuperado (al final de estas instrucciones; solo vale para la pregunta actual):
- Son fragmentos de la documentación de la plataforma (qué se publica y por qué), del catálogo de niveles y \
métricas, fichas de zonas (nombre oficial, id y barrio), ejemplos de consultas bien formadas y fichas de \
agregados ya publicados (viajes por día y barrio, y flujos entre barrios por día).
- Úsalo para explicar la plataforma, resolver nombres de zonas y barrios y elegir los parámetros de \
consultar_viajes; los ejemplos marcan el formato correcto de las llamadas.
- Una ficha de agregados solo puedes citarla tal cual, con su fecha y su barrio, si responde exactamente a \
la pregunta: no cambies su cifra, no la sumes ni la combines con otras fichas. Para cualquier otra cifra, \
para horas o zonas concretas y para el tiempo real, llama a consultar_viajes.
- Una ficha «enmascarado por privacidad» no tiene cifra: dilo así y no la estimes.
- Si respondes a partir del contexto y no de una herramienta, di de qué fuente sale (su título). No cites \
fuentes que no estén en el contexto ni le atribuyas nada que no diga.
- Si el contexto no tiene que ver con la pregunta, ignóralo.
"""

BIENVENIDA_RAG = BIENVENIDA.replace('**Asistente de datos de taxis (NYC, 2020)**',
                                    '**Asistente de datos de taxis (NYC, 2020) · versión RAG**', 1) + """

Además de consultar la plataforma puedo explicarte cómo funciona (niveles, métricas y reglas de privacidad) \
y decirte de qué fuente sale cada respuesta."""


def formatear_contexto(documentos: list[Any]) -> str:
    """Los fragmentos recuperados, numerados y con su título, tipo y fuente, para el mensaje de sistema.

    `documentos` son `langchain_core.documents.Document` (`page_content` y `metadata` con `titulo`, `tipo` y
    `fuente`); se acepta cualquier objeto con esos dos atributos.
    """
    if not documentos:
        return f'{ENCABEZADO_CONTEXTO}\n\n{SIN_CONTEXTO}'
    bloques = []
    for i, documento in enumerate(documentos, 1):
        meta = documento.metadata or {}
        titulo = meta.get('titulo') or meta.get('fuente') or f'fragmento {i}'
        etiqueta = ' · '.join(str(meta[c]) for c in ('tipo', 'fuente') if meta.get(c))
        texto = (documento.page_content or '').strip()
        if len(texto) > MAX_CARACTERES_DOCUMENTO:
            texto = texto[:MAX_CARACTERES_DOCUMENTO].rstrip() + ' […]'
        bloques.append(f'[{i}] {titulo}' + (f' ({etiqueta})' if etiqueta else '') + f'\n{texto}')
    return f'{ENCABEZADO_CONTEXTO}\n\n' + '\n\n'.join(bloques)
