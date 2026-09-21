"""Guardia de salida: revisa lo que el chatbot RAG va a enviar al proveedor externo y lleva la cuenta de tokens.

Es la última defensa de E3 en este chatbot. El agente ya solo ve agregados protegidos (no está en la red de datos
y solo habla con la API de acceso), pero antes de cada llamada al LLM se revisa el mensaje completo por si algo se
hubiera colado: campos individuales de un viaje con valor (`config/privacidad.json`, `campos_individuales`),
instantes exactos, claves de acceso o una conversación desmesurada. Si algo no puede salir, se lanza `FugaSalida`
y el agente no envía nada (agente_rag.py lo convierte en un aviso al usuario sin la cifra ni el dato).

El motivo de un rechazo nunca incluye el dato que lo provocó: se muestra al usuario.

La cuenta de tokens (`registrar`) usa `usage_metadata` de cada respuesta y no guarda contenido de la conversación.
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage

from llm import tokens_de

log = logging.getLogger('pids.chatbot_rag.salida')

RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', Path(__file__).resolve().parents[1] / 'config'))
MAX_CARACTERES = 60_000
# `id` no se vigila como campo: la herramienta buscar_zona devuelve zonas como {"id": 132, "nombre": ...}
CAMPOS_EXENTOS = {'id'}
# Secretos que nunca deben viajar en un mensaje: los de nuestro propio entorno y cualquier clave con pinta de API
VARIABLES_SECRETAS = ('LLM_API_KEY', 'ACCESO_CLAVE', 'CAPTURA_CLAVE')
CLAVE_API = re.compile(r'\bsk-[A-Za-z0-9_\-]{16,}')
CABECERA_CLAVE = re.compile(r'(?i)\b(x-api-key|authorization)\s*[:=]\s*\S+')
# Un instante con minutos o segundos distintos de cero solo puede venir de un viaje concreto: los agregados van a la
# hora en punto (2020-01-15T08:00:00) y las fichas hablan de días
INSTANTE_EXACTO = re.compile(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:(?!00\b)\d{2}(?::\d{2})?\b|'
                             r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:00:(?!00\b)\d{2}\b')


class FugaSalida(RuntimeError):
    """Algo que no debe salir del equipo iba a enviarse al proveedor: campos individuales, claves, instantes exactos."""


@lru_cache(maxsize=1)
def campos_individuales() -> tuple[str, ...]:
    cfg = json.loads((RUTA_CONFIG / 'privacidad.json').read_text(encoding='utf-8'))
    return tuple(c for c in cfg['campos_individuales'] if c not in CAMPOS_EXENTOS)


@lru_cache(maxsize=1)
def _patron_campos() -> re.Pattern[str]:
    """Un campo individual **con valor**, en forma de dato estructurado: "recogida": "...", 'matricula': ..., tarifa=12.

    En prosa («no hay datos de conductores») no se dispara: hace falta el separador y un valor que no sea nulo.
    """
    campos = '|'.join(re.escape(c) for c in campos_individuales())
    return re.compile(rf'''(?<![\w.])["']?\b({campos})\b["']?\s*[:=]\s*(?!null\b|None\b|""|''|\s)''', re.IGNORECASE)


def texto_de(mensaje: BaseMessage) -> str:
    """Todo lo que un mensaje lleva hacia el proveedor: contenido y, en el asistente, sus llamadas a herramientas."""
    partes = []
    contenido = mensaje.content
    if isinstance(contenido, str):
        partes.append(contenido)
    elif isinstance(contenido, list):
        partes.append(json.dumps(contenido, ensure_ascii=False, default=str))
    llamadas = getattr(mensaje, 'tool_calls', None)
    if llamadas:
        partes.append(json.dumps(llamadas, ensure_ascii=False, default=str))
    return '\n'.join(partes)


def _secretos() -> list[str]:
    return [v for v in (os.environ.get(n, '').strip() for n in VARIABLES_SECRETAS) if len(v) >= 8]


def motivos_de(texto: str) -> list[str]:
    """Qué impide enviar un texto. Lista vacía si puede salir. Nunca incluye el dato encontrado."""
    motivos = []
    if campos := sorted({m.group(1).lower() for m in _patron_campos().finditer(texto)}):
        motivos.append(f'contiene campos individuales de un viaje con valor ({", ".join(campos)})')
    if INSTANTE_EXACTO.search(texto):
        motivos.append('contiene un instante exacto (con minutos o segundos), propio de un viaje concreto')
    if CLAVE_API.search(texto) or CABECERA_CLAVE.search(texto) or any(s in texto for s in _secretos()):
        motivos.append('contiene una clave de acceso')
    return motivos


class GuardiaSalida:
    """Cumple el protocolo `Guardia` de agente_rag.py: `revisar` antes de cada llamada al LLM y `registrar` después."""

    def __init__(self, max_caracteres: int = MAX_CARACTERES):
        self.max_caracteres = max_caracteres
        self.llamadas = 0
        self._tokens = {'entrada': 0, 'salida': 0, 'razonamiento': 0, 'total': 0}

    def revisar(self, mensajes: list[BaseMessage]) -> list[BaseMessage]:
        total = 0
        for posicion, mensaje in enumerate(mensajes):
            texto = texto_de(mensaje)
            total += len(texto)
            if motivos := motivos_de(texto):
                raise FugaSalida(f'el mensaje {posicion + 1} ({mensaje.type}) {"; ".join(motivos)}')
        if total > self.max_caracteres:
            raise FugaSalida(f'la conversación ocupa {total} caracteres y el máximo es {self.max_caracteres}: '
                             'empieza una conversación nueva')
        return mensajes

    def registrar(self, respuesta: AIMessage) -> None:
        uso = tokens_de(respuesta)
        for clave in self._tokens:
            self._tokens[clave] += uso.get(clave, 0)
        self.llamadas += 1
        log.info('salida: llamada %d, %d tokens (%d de entrada, %d de salida); acumulado %d',
                 self.llamadas, uso['total'], uso['entrada'], uso['salida'], self._tokens['total'])

    @property
    def tokens(self) -> dict[str, int]:
        return dict(self._tokens)
