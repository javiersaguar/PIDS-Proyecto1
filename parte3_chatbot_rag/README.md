# Parte 3 bis · Chatbot RAG

Chainlit + LangChain con un LLM externo compatible con OpenAI (Helmcode, infraestructura en la UE) y recuperación
de contexto en Qdrant. Reutiliza sin modificarlos el cliente de la API, el filtro previo y las barreras sobre las
cifras del chatbot de Ollama (`../parte3_chatbot/`), que sigue igual.

| Fichero | Contenido |
|---|---|
| `llm.py` | Fábrica del modelo de chat, embeddings y rerank; lista blanca de modelos que no salen de la UE |
| `comprobar_llm.py` | Comprobación del proveedor de punta a punta (`make rag-comprobar`) |
| `corpus.py`, `corpus/`, `fichas.py`, `indexar.py` | Corpus de conocimiento, fichas de agregados y su indexación en Qdrant (`make rag-indexar`) |
| `recuperador.py` | Búsqueda en las dos colecciones, filtros por día y barrio, rerank opcional |
| `agente_rag.py`, `herramientas_lc.py`, `prompts_rag.py` | El agente sin interfaz: filtro previo, contexto, herramientas y barreras |
| `salida.py` | Guardia de salida: qué puede viajar al proveedor y cuenta de tokens |
| `fabrica.py`, `app.py`, `chainlit.md` | Construcción del agente e interfaz de Chainlit (http://localhost:8011) |
| `casos_de_uso_rag.py`, `bateria_trampa_rag.py`, `comparar.py` | Suites de evaluación y comparativa con el chatbot de Ollama |
| `CONTRATOS.md` | Reparto del trabajo en cinco bloques, firmas y orden de integración |

- **Arranque:** `make entorno-completar` (pega `LLM_API_KEY` en `.env`), `make chatbot-rag`, `make rag-indexar`.
- **Documentación, decisión E3 y resultados medidos:** [`../docs/chatbot_rag.md`](../docs/chatbot_rag.md).
- **Pruebas sin red:** `make test` (Qdrant en memoria, embeddings y LLM falsos).
- **Pruebas con el agente real:** `make rag-casos`, `make rag-bateria`, `make rag-comparar`; informes en
  `informes/chatbot_rag/` (no se versiona).
