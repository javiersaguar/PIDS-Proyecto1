# Comparativa de tecnologías

Criterios: encaje con la restricción E3 (privacidad total), madurez, facilidad de despliegue en un
portátil con Docker (WSL2), coste de aprendizaje para el grupo y relación con la asignatura.

| Componente | Elegida | Alternativas evaluadas | Por qué |
|---|---|---|---|
| Despliegue | **Docker Compose** | Kubernetes (minikube, k3s) | Un fichero levanta todo y cualquiera lo reproduce; Kubernetes añade mucha complejidad para una prueba de concepto |
| Cola de eventos | **Redpanda** | Apache Kafka, RabbitMQ, Mosquitto (MQTT) | API compatible con Kafka (los clientes y el conector de Spark son los mismos) en un solo contenedor, sin JVM, y arranca en segundos. RabbitMQ no conserva el histórico de eventos; MQTT no sirve como registro |
| Procesado | **Spark 4.0 en Scala, standalone, modo cluster** | pandas, Polars/DuckDB, PySpark | El mismo código sirve para lotes y streaming, así que histórico y tiempo real aplican exactamente las mismas reglas (requisito de E3). El modo cluster (el driver corre dentro del clúster) solo admite Java/Scala en standalone; por eso Scala |
| Base de datos | **MongoDB** | PostgreSQL | Documentos por nivel de agregación con esquema flexible (niveles nuevos sin migraciones); permisos por colección con roles propios (auditoría de solo inserción) |
| Objetos | **SeaweedFS (S3)** | MinIO, Garage, RustFS | MinIO ya no publica imágenes (su repositorio de Docker Hub no existe y la última versión en quay.io es de 2025). SeaweedFS es maduro, Apache 2.0, y permite identidades con permisos por bucket en un fichero |
| Privacidad | **Reglas propias** | Privacidad diferencial (OpenDP), Presidio | Umbral k, generalización temporal y espacial y lista de campos prohibidos: explicable y comprobable con tests. La privacidad diferencial queda como trabajo futuro |
| APIs | **FastAPI** | Flask, PostgREST | Validación con Pydantic, documentación automática en `/docs`, asíncrona; permite programar el filtro de privacidad y la auditoría |
| Visualización | **Grafana + Prometheus** | Metabase, Superset, Streamlit | Paneles y alertas; se configura con ficheros (despliegue automático). Grafana solo ve métricas: no tiene credenciales de datos |
| Orquestación | **Airflow 3** | cron, Dagster | Estándar en la asignatura; DAG con reintentos, parámetros e interfaz. `SparkSubmitOperator` envía en modo cluster por la pasarela REST del máster y sigue el estado del driver |
| Plataforma del chatbot | **LLM local (Ollama) con herramientas** | Rasa, Dialogflow, LLM en la nube | Ninguna pregunta ni dato sale del equipo (E3). Dialogflow y los LLM en la nube envían las conversaciones a terceros. Rasa exige entrenar intenciones y su versión abierta está prácticamente abandonada |
| Segundo chatbot: LLM externo | **Helmcode** (API compatible con OpenAI; `deepseek-v4-flash`, `qwen3.6`) | OpenAI, Anthropic, Google; solo Ollama | Modelos abiertos en infraestructura de la UE y sin registro de prompts: el compromiso más defendible en E3 para un modelo mayor que el local, sin GPU y con tool calling más fiable. Los proveedores de EE. UU. quedan vetados por lista blanca (`llm.py`). Detalle en [`chatbot_rag.md`](chatbot_rag.md) |
| Recuperación (RAG) | **Qdrant** + **LangChain** | Chroma embebido, FAISS, pgvector; LlamaIndex | Qdrant es un servicio más en Compose, con filtros por metadatos (día, barrio) y panel; LangChain aporta el modelo de chat compatible con OpenAI, las herramientas y los trozeadores. El índice solo contiene documentación pública y agregados ya protegidos |
| Interfaz del chat | **Chainlit** | Streamlit, Open WebUI, Telegram | Hecho para chats en Python, con botones de acción (útiles para los gestos). Telegram haría pasar los mensajes por sus servidores |
| Cliente del LLM (chatbot de Ollama) | **Cliente directo de Ollama** | LangChain, LlamaIndex | Tres herramientas: sin capas intermedias es más fácil de auditar qué llama el modelo. El chatbot RAG sí usa LangChain, porque cambia de proveedor y añade recuperación |
| Gestos → chatbot | **HTTP + SSE** | WebSocket, MQTT | SSE basta para un flujo en un solo sentido y funciona sobre HTTP normal. Desde Windows se usa HTTP para evitar la DLL nativa de Kafka (Smart App Control) |

## Versiones fijadas

Spark 4.0.4 (Scala 2.13.16, Java 17) · conector MongoDB 11.1.0 · hadoop-aws 3.4.1 · Redpanda 25.2.1 ·
MongoDB 8.0 · SeaweedFS 4.47 · Airflow 3.3.2 (proveedor Spark 6.3.2) · Prometheus 3.1.0 ·
Grafana 11.5.1 · Ollama 0.34.1 · Python 3.12 · FastAPI 0.141 · Chainlit 2.12 · LangChain 1.4
(langchain-openai 1.6, langchain-qdrant 1.1) · Qdrant 1.19.1 (cliente 1.19.0) · Helmcode: `deepseek-v4-flash`,
`qwen3-embedding` (4096 dimensiones) y `rerank`.

## Arquitecturas alternativas consideradas

- **Todo en PostgreSQL** (zonas por esquema y permisos por columna): más simple, pero sin almacenamiento
  de objetos ni base de documentos (el enunciado valora varias opciones de almacenamiento).
- **Kafka + consumidores Python** en lugar de Spark: menos infraestructura, pero habría que duplicar la
  lógica entre histórico y tiempo real, que es justo lo que E3 pide evitar.
