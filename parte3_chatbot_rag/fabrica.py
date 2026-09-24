"""Construcción de los agentes listos para usar: el chatbot RAG (Mistral + LangChain + Qdrant) y el de Ollama.

Lo usan la interfaz (app.py) y las suites de evaluación (casos_de_uso_rag.py, bateria_trampa_rag.py y
comparar.py), para que todos construyan el agente exactamente igual. Las piezas vienen de:
  - llm.obtener_llm()                  el modelo del proveedor (Mistral), con la lista blanca de modelos de la UE
  - recuperador.obtener_recuperador()  las dos colecciones de Qdrant (conocimiento y fichas de agregados)
  - salida.GuardiaSalida()             revisa lo que sale hacia el proveedor y cuenta los tokens de la sesión
  - agente_rag.AgenteRAG               el agente: filtro previo, recuperación, herramientas y barreras
Esos módulos se importan al construir el agente, no al cargar este fichero: así las pruebas y los scripts que
solo necesitan el agente de Ollama funcionan sin LangChain.

Cada agente sale acompañado de un contador de tokens (entrada + salida) para medir el coste por pregunta.

Configuración: en el contenedor llega por el entorno (Compose). Desde el host se lee `.env` y las URL de los
servicios se derivan de los puertos publicados (`PUERTO_ACCESO`, `PUERTO_QDRANT`, `PUERTO_OLLAMA`), porque
los nombres de los contenedores (`acceso`, `qdrant`, `ollama`) no resuelven fuera de Docker.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from herramientas import ClienteAcceso

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:                      # sin el grupo `rag` instalado solo se puede construir el de Ollama
    BaseCallbackHandler = object         # type: ignore[assignment,misc]

RAIZ = Path(__file__).resolve().parents[1]
EN_CONTENEDOR = Path('/.dockerenv').exists() or os.environ.get('PIDS_CONFIG_DIR', '').startswith('/app')
MODELO_RAG_POR_DEFECTO = 'ministral-14b-latest'      # el de llm.PROVEEDORES['api.mistral.ai']
# variable de la URL -> (servicio en Compose, variable del puerto publicado, puerto por defecto)
SERVICIOS = {
    'ACCESO_URL': ('acceso', 'PUERTO_ACCESO', '8002'),
    'QDRANT_URL': ('qdrant', 'PUERTO_QDRANT', '6333'),
    'OLLAMA_URL': ('ollama', 'PUERTO_OLLAMA', '11435'),
}


# --- entorno -----------------------------------------------------------------------------------------------

def entorno(ruta: Path = RAIZ / '.env') -> dict[str, str]:
    """Pares CLAVE=valor de .env (si existe); el entorno del proceso tiene prioridad."""
    valores = {}
    if ruta.is_file():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            if linea.strip() and not linea.lstrip().startswith('#') and '=' in linea:
                clave, valor = linea.split('=', 1)
                valores[clave.strip()] = valor.strip().strip('"\'')
    return {**valores, **os.environ}


def url_servicio(variable: str, cfg: dict[str, str] | None = None) -> str:
    """URL de un servicio: la del entorno en el contenedor; en el host, la del puerto publicado en 127.0.0.1.

    Fuera de Docker, una URL cuyo anfitrión es el nombre de un contenedor (`http://qdrant:6333`, que es lo que
    trae .env) no sirve, así que se sustituye por el puerto publicado. Una URL con anfitrión resoluble
    (localhost, una IP, un dominio) se respeta.
    """
    cfg = cfg if cfg is not None else entorno()
    servicio, puerto_variable, puerto = SERVICIOS[variable]
    url = cfg.get(variable, '')
    anfitrion = urlparse(url).hostname if url else None
    if url and (EN_CONTENEDOR or anfitrion != servicio):
        return url
    return f'http://127.0.0.1:{cfg.get(puerto_variable, puerto)}'


def exportar_entorno() -> dict[str, str]:
    """Deja en os.environ lo que los módulos del chatbot RAG leen del entorno (LLM_*, QDRANT_URL, RAG_*).

    En el contenedor no cambia nada (todo viene ya de Compose). Desde el host permite ejecutar los scripts con
    `uv run` sin hacer `source .env`. Devuelve la configuración resultante.
    """
    cfg = entorno()
    for variable in SERVICIOS:
        cfg[variable] = url_servicio(variable, cfg)
    for clave, valor in cfg.items():
        if clave in SERVICIOS or clave.startswith(('LLM_', 'RAG_')):
            os.environ[clave] = valor
    return cfg


def cliente_acceso(nombre: str = 'chatbot_rag') -> ClienteAcceso:
    """Cliente de la API de acceso con la clave del cliente indicado (así la auditoría distingue los chatbots).

    En el contenedor manda ACCESO_CLAVE (Compose); en el host se toma ACCESO_CLAVE_<NOMBRE> de .env, o la del
    equipo si no existe.
    """
    cfg = entorno()
    clave = (cfg.get('ACCESO_CLAVE') or cfg.get(f'ACCESO_CLAVE_{nombre.upper()}')
             or cfg.get('ACCESO_CLAVE_EQUIPO') or '')
    return ClienteAcceso(url=url_servicio('ACCESO_URL', cfg), clave=clave)


def modelo_rag() -> str:
    return entorno().get('LLM_MODELO') or MODELO_RAG_POR_DEFECTO


# --- contadores de tokens ----------------------------------------------------------------------------------

class ContadorTokens(BaseCallbackHandler):        # type: ignore[misc,valid-type]
    """Suma los tokens (entrada + salida) de cada respuesta del LLM de LangChain.

    Se engancha al modelo como callback del constructor (`llm.callbacks = [contador]`), que es lo único que
    sobrevive a `bind_tools`: `with_config` se pierde al volver a envolver el modelo con las herramientas.
    """
    run_inline = True

    def __init__(self) -> None:
        super().__init__()
        self.tokens = 0
        self.llamadas = 0

    def on_llm_end(self, response: Any, **_: Any) -> None:
        self.llamadas += 1
        self.tokens += tokens_de_respuesta(response)


def tokens_de_respuesta(response: Any) -> int:
    """Tokens de un LLMResult: usage_metadata de cada mensaje o, si no viene, token_usage de llm_output."""
    total = 0
    for generaciones in getattr(response, 'generations', None) or []:
        for generacion in generaciones:
            uso = getattr(getattr(generacion, 'message', None), 'usage_metadata', None) or {}
            total += int(uso.get('total_tokens') or (uso.get('input_tokens') or 0) + (uso.get('output_tokens') or 0))
    if not total:
        uso = (getattr(response, 'llm_output', None) or {}).get('token_usage') or {}
        total = int(uso.get('total_tokens') or (uso.get('prompt_tokens') or 0) + (uso.get('completion_tokens') or 0))
    return total


class OllamaContado:
    """Envuelve al cliente de Ollama para sumar los tokens de cada chat (el agente solo usa `chat`)."""

    def __init__(self, cliente: Any) -> None:
        self.cliente = cliente
        self.tokens = 0
        self.llamadas = 0

    async def chat(self, **argumentos: Any) -> Any:
        respuesta = await self.cliente.chat(**argumentos)
        self.llamadas += 1
        self.tokens += int(getattr(respuesta, 'prompt_eval_count', 0) or 0) + int(getattr(respuesta, 'eval_count', 0) or 0)
        return respuesta


# --- agentes -----------------------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _recuperador(k: int, rerank: bool):
    """Uno por proceso: el cliente de Qdrant y el de embeddings no guardan estado de la conversación."""
    from recuperador import obtener_recuperador
    return obtener_recuperador(k=k, rerank=rerank)


def agente_rag(acceso: ClienteAcceso, k: int | None = None, rerank: bool | None = None,
               temperatura: float | None = None, modelo: str | None = None):
    """El agente RAG real y su contador de tokens. Una conversación nueva por llamada."""
    cfg = exportar_entorno()
    from agente_rag import AgenteRAG
    from llm import obtener_llm
    from salida import GuardiaSalida

    k = k if k is not None else int(cfg.get('RAG_K') or 6)
    rerank = rerank if rerank is not None else (cfg.get('RAG_RERANK') or 'false').lower() == 'true'
    contador = ContadorTokens()
    llm = obtener_llm(temperatura=temperatura, modelo=modelo)
    llm.callbacks = [contador]
    agente = AgenteRAG(acceso, llm, _recuperador(k, rerank), guardia=GuardiaSalida(), k=k)
    return agente, contador


def agente_ollama(acceso: ClienteAcceso, host: str | None = None, opciones: dict | None = None):
    """El chatbot actual (parte3_chatbot) con su contador de tokens, para compararlo con el RAG."""
    from agente import Agente
    from ollama import AsyncClient

    contador = OllamaContado(AsyncClient(host=host or url_servicio('OLLAMA_URL')))
    return Agente(acceso, contador, opciones=opciones), contador
