"""Las herramientas del agente como `StructuredTool` de LangChain.

Mismos nombres y esquemas que `parte3_chatbot/herramientas.ESQUEMAS` (se construyen a partir de ellos, no se
copian) y misma ejecución: cada una delega en `ClienteAcceso.ejecutar`, así que el LLM sigue sin ver nada
que no venga de la API de acceso, y las correcciones de formato del cliente y el filtro de la API se aplican
igual que en el chatbot de Ollama.
"""
from __future__ import annotations

import copy
from typing import Any

from langchain_core.tools import StructuredTool

from agente import Ejecutor
from herramientas import ESQUEMAS, ClienteAcceso

NOMBRES: list[str] = [esquema['function']['name'] for esquema in ESQUEMAS]


def herramientas_langchain(acceso: ClienteAcceso | None = None,
                           ejecutar: Ejecutor | None = None) -> list[StructuredTool]:
    """Una herramienta por esquema. `ejecutar(nombre, argumentos)` es quien la ejecuta; por defecto,
    `acceso.ejecutar` (la interfaz pasa una versión que además muestra el paso)."""
    if ejecutar is None:
        if acceso is None:
            raise ValueError('hace falta un ClienteAcceso o una función ejecutar(nombre, argumentos)')
        ejecutar = acceso.ejecutar
    return [_herramienta(esquema['function'], ejecutar) for esquema in ESQUEMAS]


def _herramienta(funcion: dict, ejecutar: Ejecutor) -> StructuredTool:
    nombre = funcion['name']

    async def correr(**argumentos: Any) -> Any:
        return await ejecutar(nombre, argumentos)

    # El esquema JSON se pasa tal cual: LangChain lo envía al proveedor sin convertirlo a Pydantic
    return StructuredTool.from_function(coroutine=correr, name=nombre, description=funcion['description'],
                                        args_schema=copy.deepcopy(funcion['parameters']))
