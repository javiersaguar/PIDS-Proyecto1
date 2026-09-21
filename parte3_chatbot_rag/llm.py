"""Proveedor del LLM del chatbot RAG: Helmcode, una API compatible con OpenAI en infraestructura de la UE y sin logs.

Es el único punto del chatbot RAG que construye clientes hacia el proveedor externo. Reglas (E3, docs/chatbot_rag.md):
  - Solo se admiten los modelos que Helmcode ejecuta en sus propias máquinas (MODELOS_UE). Los que revende de
    Anthropic, OpenAI y Google salen de la UE y se cobran aparte: se rechazan aunque la clave los listara.
  - La clave sale de LLM_API_KEY (.env) y no se escribe nunca en logs ni en el repositorio.
  - Qué se envía al proveedor lo decide el agente (agente_rag.py) y lo revisa la guardia de salida (salida.py):
    preguntas y agregados ya protegidos, nunca datos individuales.

Medido el 21/09/2026 contra la API real:
  - el razonamiento llega aparte, en `reasoning_content`, así que `content` es solo la respuesta; LangChain no
    conserva ese texto (solo su recuento de tokens, en `usage_metadata`). `reasoning_effort` lo controla en
    qwen3.6 y gemma4 (`none` lo apaga) y no tiene efecto en deepseek-v4-flash, que decide por sí mismo;
  - las llamadas a herramientas con el esquema JSON de OpenAI funcionan con deepseek-v4-flash (~2 s) y con
    qwen3.6 con `reasoning_effort=none` (~1 s);
  - límites por clave: 100 peticiones/min y 10 simultáneas (5 en qwen3.6 y gemma4); embeddings 60/min en lotes
    de 32 textos, 4096 dimensiones. Los 429 los reintenta el cliente con espera exponencial.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

BASE_URL_POR_DEFECTO = 'https://api.helmcode.com/v1'
MODELO_POR_DEFECTO = 'deepseek-v4-flash'
EMBEDDINGS_POR_DEFECTO = 'qwen3-embedding'
# Modelos que Helmcode ejecuta en la UE (helmcode.com/docs/models). Fuera quedan los revendidos: claude-*, gpt-*,
# gemini-*. Si Helmcode añade un modelo propio, se añade aquí tras comprobarlo con comprobar_llm.py.
MODELOS_UE = frozenset({
    'deepseek-v4-flash', 'qwen3.6', 'gemma4', 'glm5.3', 'glm5.3-flash', 'glm5.2',
    'qwen3-embedding', 'rerank',
})
DIMENSION_EMBEDDINGS = 4096
LOTE_EMBEDDINGS = 32                    # límite del endpoint /v1/embeddings
NIVELES_RAZONAMIENTO = ('none', 'minimal', 'low', 'medium', 'high', 'max')


class ModeloNoPermitido(ValueError):
    """El modelo no está en la lista blanca de modelos que no salen de la UE."""


class FaltaClave(RuntimeError):
    """No hay LLM_API_KEY en el entorno."""


def base_url() -> str:
    return os.environ.get('LLM_BASE_URL', '').strip() or BASE_URL_POR_DEFECTO


def clave() -> str:
    valor = os.environ.get('LLM_API_KEY', '').strip()
    if not valor:
        raise FaltaClave('Falta LLM_API_KEY: pega la clave del panel de Helmcode en .env (make entorno-completar)')
    return valor


def cabeceras() -> dict[str, str]:
    return {'Authorization': f'Bearer {clave()}'}


def modelo_permitido(modelo: str) -> bool:
    return modelo.strip() in MODELOS_UE


def comprobar_modelo(modelo: str) -> str:
    modelo = modelo.strip()
    if not modelo_permitido(modelo):
        raise ModeloNoPermitido(f'{modelo!r} no está en la lista de modelos que se ejecutan en la UE: '
                                f'{", ".join(sorted(MODELOS_UE))}')
    return modelo


def _flotante(nombre: str, por_defecto: float) -> float:
    valor = os.environ.get(nombre, '').strip()
    return float(valor) if valor else por_defecto


def obtener_llm(temperatura: float | None = None, modelo: str | None = None, razonamiento: str | None = None,
                **opciones: Any) -> ChatOpenAI:
    """Modelo de chat con herramientas. Lee LLM_MODELO, LLM_TEMPERATURA y LLM_RAZONAMIENTO si no se indican.

    `razonamiento` es el `reasoning_effort` de Helmcode (`none` ... `max`); vacío = el del modelo.
    Siempre por /chat/completions: es lo que el proveedor garantiza compatible.
    """
    modelo = comprobar_modelo(modelo or os.environ.get('LLM_MODELO', MODELO_POR_DEFECTO))
    if temperatura is None:
        temperatura = _flotante('LLM_TEMPERATURA', 0.2)
    razonamiento = (razonamiento if razonamiento is not None else os.environ.get('LLM_RAZONAMIENTO', '')).strip()
    if razonamiento and razonamiento not in NIVELES_RAZONAMIENTO:
        raise ValueError(f'LLM_RAZONAMIENTO debe ser uno de {", ".join(NIVELES_RAZONAMIENTO)}')
    return ChatOpenAI(
        model=modelo, base_url=base_url(), api_key=clave(), temperature=temperatura,
        timeout=_flotante('LLM_TIMEOUT_SEGUNDOS', 90), max_retries=3, use_responses_api=False,
        reasoning_effort=razonamiento or None, **opciones)


def obtener_embeddings(modelo: str | None = None) -> OpenAIEmbeddings:
    """Embeddings de 4096 dimensiones. Sin comprobación de longitud con tiktoken (no es un modelo de OpenAI)
    y en lotes de 32, que es el máximo del endpoint."""
    modelo = comprobar_modelo(modelo or os.environ.get('LLM_MODELO_EMBEDDINGS', EMBEDDINGS_POR_DEFECTO))
    return OpenAIEmbeddings(model=modelo, base_url=base_url(), api_key=clave(), check_embedding_ctx_length=False,
                            chunk_size=LOTE_EMBEDDINGS, max_retries=5, timeout=60)


async def modelos_disponibles(cliente: httpx.AsyncClient | None = None) -> list[str]:
    """Identificadores que la clave puede usar según /v1/models (permitidos o no: filtrar con modelo_permitido)."""
    async def pedir(http: httpx.AsyncClient) -> list[str]:
        r = await http.get(f'{base_url()}/models', headers=cabeceras())
        r.raise_for_status()
        return sorted(m['id'] for m in r.json().get('data', []) if m.get('id'))
    if cliente is not None:
        return await pedir(cliente)
    async with httpx.AsyncClient(timeout=30) as http:
        return await pedir(http)


async def reordenar(pregunta: str, documentos: list[str], top_n: int | None = None,
                    cliente: httpx.AsyncClient | None = None) -> list[tuple[int, float]]:
    """Reordena textos por relevancia con /v1/rerank. Devuelve (índice en `documentos`, puntuación), de mayor a menor."""
    if not documentos:
        return []
    cuerpo = {'model': comprobar_modelo('rerank'), 'query': pregunta, 'documents': documentos,
              'top_n': top_n or len(documentos)}

    async def pedir(http: httpx.AsyncClient) -> list[tuple[int, float]]:
        r = await http.post(f'{base_url()}/rerank', headers=cabeceras(), json=cuerpo)
        r.raise_for_status()
        resultados = [(int(x['index']), float(x['relevance_score'])) for x in r.json().get('results', [])]
        return sorted(resultados, key=lambda par: par[1], reverse=True)
    if cliente is not None:
        return await pedir(cliente)
    async with httpx.AsyncClient(timeout=60) as http:
        return await pedir(http)


def razonamiento_de(mensaje: AIMessage) -> str | None:
    """El razonamiento que el proveedor devuelve aparte de la respuesta, si el cliente lo conserva (la versión
    actual de LangChain no lo hace: devuelve None). Nunca se muestra al usuario."""
    extra = mensaje.additional_kwargs or {}
    valor = extra.get('reasoning_content') or extra.get('reasoning')
    return str(valor) if valor else None


def tokens_de(mensaje: AIMessage) -> dict[str, int]:
    """Tokens de entrada, salida y razonamiento de una respuesta, para la guardia de salida y las mediciones."""
    uso = mensaje.usage_metadata or {}
    detalles = uso.get('output_token_details') or {}
    return {'entrada': int(uso.get('input_tokens', 0)), 'salida': int(uso.get('output_tokens', 0)),
            'razonamiento': int(detalles.get('reasoning', 0)), 'total': int(uso.get('total_tokens', 0))}
