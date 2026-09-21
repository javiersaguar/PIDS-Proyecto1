"""Proveedor LLM del chatbot RAG (parte3_chatbot_rag/llm.py): lista blanca, configuración y llamadas HTTP simuladas."""
import sys
from pathlib import Path

import httpx
import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'parte3_chatbot_rag'))

import llm as L  # noqa: E402


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'clave-de-prueba')
    monkeypatch.setenv('LLM_BASE_URL', 'https://proveedor.prueba/v1')
    for variable in ('LLM_MODELO', 'LLM_MODELO_EMBEDDINGS', 'LLM_TEMPERATURA', 'LLM_RAZONAMIENTO', 'LLM_TIMEOUT_SEGUNDOS'):
        monkeypatch.delenv(variable, raising=False)


# --- lista blanca ------------------------------------------------------------------------------------

@pytest.mark.parametrize('modelo', ['deepseek-v4-flash', 'qwen3.6', 'gemma4', 'qwen3-embedding', 'rerank', ' qwen3.6 '])
def test_modelos_ue_permitidos(modelo):
    assert L.modelo_permitido(modelo)


@pytest.mark.parametrize('modelo', ['claude-sonnet-5', 'gpt-5.6-sol', 'gemini-3.6-flash', 'whisper', 'gpt-4o'])
def test_modelos_revendidos_vetados(modelo):
    assert not L.modelo_permitido(modelo)
    with pytest.raises(L.ModeloNoPermitido):
        L.obtener_llm(modelo=modelo)
    with pytest.raises(L.ModeloNoPermitido):
        L.obtener_embeddings(modelo=modelo)


def test_modelo_vacio_es_el_por_defecto():
    assert not L.modelo_permitido('')
    assert L.obtener_llm(modelo='').model_name == 'deepseek-v4-flash'


def test_el_modelo_del_entorno_tambien_pasa_por_la_lista(monkeypatch):
    monkeypatch.setenv('LLM_MODELO', 'claude-opus-5')
    with pytest.raises(L.ModeloNoPermitido):
        L.obtener_llm()


# --- configuración -----------------------------------------------------------------------------------

def test_llm_por_defecto():
    chat = L.obtener_llm()
    assert chat.model_name == 'deepseek-v4-flash'
    assert chat.openai_api_base == 'https://proveedor.prueba/v1'
    assert chat.temperature == 0.2
    assert chat.use_responses_api is False
    assert chat.reasoning_effort is None
    assert chat.openai_api_key.get_secret_value() == 'clave-de-prueba'


def test_llm_lee_el_entorno(monkeypatch):
    monkeypatch.setenv('LLM_MODELO', 'qwen3.6')
    monkeypatch.setenv('LLM_TEMPERATURA', '0')
    monkeypatch.setenv('LLM_RAZONAMIENTO', 'none')
    chat = L.obtener_llm()
    assert (chat.model_name, chat.temperature, chat.reasoning_effort) == ('qwen3.6', 0.0, 'none')


def test_los_argumentos_mandan_sobre_el_entorno(monkeypatch):
    monkeypatch.setenv('LLM_MODELO', 'qwen3.6')
    chat = L.obtener_llm(temperatura=0.7, modelo='gemma4', razonamiento='low')
    assert (chat.model_name, chat.temperature, chat.reasoning_effort) == ('gemma4', 0.7, 'low')


def test_razonamiento_desconocido():
    with pytest.raises(ValueError):
        L.obtener_llm(razonamiento='muchisimo')


def test_sin_clave(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', '  ')
    with pytest.raises(L.FaltaClave):
        L.obtener_llm()
    with pytest.raises(L.FaltaClave):
        L.obtener_embeddings()


def test_base_url_por_defecto(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL', '')
    assert L.base_url() == 'https://api.helmcode.com/v1'


def test_embeddings_sin_tiktoken_y_en_lotes_de_32():
    emb = L.obtener_embeddings()
    assert emb.model == 'qwen3-embedding'
    assert emb.check_embedding_ctx_length is False          # el endpoint no es de OpenAI: textos tal cual
    assert emb.chunk_size == L.LOTE_EMBEDDINGS == 32          # máximo del endpoint
    assert emb.openai_api_base == 'https://proveedor.prueba/v1'
    assert L.DIMENSION_EMBEDDINGS == 4096


def test_la_clave_no_aparece_en_la_representacion():
    assert 'clave-de-prueba' not in repr(L.obtener_llm())
    assert 'clave-de-prueba' not in repr(L.obtener_embeddings())


# --- llamadas HTTP simuladas -------------------------------------------------------------------------

def _cliente(respuesta: dict, capturadas: list) -> httpx.AsyncClient:
    def manejar(peticion: httpx.Request) -> httpx.Response:
        capturadas.append(peticion)
        return httpx.Response(200, json=respuesta)
    return httpx.AsyncClient(transport=httpx.MockTransport(manejar))


async def test_modelos_disponibles():
    capturadas: list = []
    cliente = _cliente({'data': [{'id': 'qwen3.6'}, {'id': 'claude-sonnet-5'}, {'id': 'deepseek-v4-flash'}]}, capturadas)
    assert await L.modelos_disponibles(cliente) == ['claude-sonnet-5', 'deepseek-v4-flash', 'qwen3.6']
    assert capturadas[0].url == 'https://proveedor.prueba/v1/models'
    assert capturadas[0].headers['Authorization'] == 'Bearer clave-de-prueba'


async def test_reordenar_devuelve_indices_por_puntuacion():
    capturadas: list = []
    cliente = _cliente({'results': [{'index': 2, 'relevance_score': 0.2}, {'index': 0, 'relevance_score': 0.9}]}, capturadas)
    orden = await L.reordenar('aeropuerto', ['JFK', 'Times Sq', 'LaGuardia'], top_n=2, cliente=cliente)
    assert orden == [(0, 0.9), (2, 0.2)]
    import json
    cuerpo = json.loads(capturadas[0].content)
    assert cuerpo == {'model': 'rerank', 'query': 'aeropuerto', 'documents': ['JFK', 'Times Sq', 'LaGuardia'], 'top_n': 2}


async def test_reordenar_sin_documentos_no_llama():
    capturadas: list = []
    assert await L.reordenar('x', [], cliente=_cliente({}, capturadas)) == []
    assert capturadas == []


# --- ayudas sobre la respuesta -----------------------------------------------------------------------

def test_tokens_de_la_respuesta():
    mensaje = AIMessage(content='listo', usage_metadata={
        'input_tokens': 39, 'output_tokens': 15, 'total_tokens': 54, 'output_token_details': {'reasoning': 12}})
    assert L.tokens_de(mensaje) == {'entrada': 39, 'salida': 15, 'razonamiento': 12, 'total': 54}
    assert L.tokens_de(AIMessage(content='')) == {'entrada': 0, 'salida': 0, 'razonamiento': 0, 'total': 0}


def test_razonamiento_de_la_respuesta():
    assert L.razonamiento_de(AIMessage(content='x')) is None
    assert L.razonamiento_de(AIMessage(content='x', additional_kwargs={'reasoning_content': 'pienso'})) == 'pienso'
