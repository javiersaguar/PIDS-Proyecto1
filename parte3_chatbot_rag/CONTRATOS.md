# Chatbot RAG · contratos para el trabajo en paralelo

Segundo chatbot de la parte 3: **LangChain + Qdrant + LLM externo compatible con OpenAI (Helmcode)**. El chatbot
de Ollama (`parte3_chatbot/`) sigue igual y es la alternativa si este no convence. Este fichero es el acuerdo
entre los cinco bloques de trabajo: quién posee qué ficheros y qué firmas exponen. **No lo edita nadie más que el
Agente 1**; si un contrato tiene que cambiar, se pide en el PR y se cambia aquí.

Estado: **fase 0 hecha el 21/09/2026** (rama `tarea/rag-base`): dependencias, variables, Compose, `llm.py`
comprobado contra la API real y este documento.

## 1. Diseño

- **Híbrido.** Qdrant guarda *conocimiento* (docs del repo, catálogo de la API, las 265 zonas, reglas E3, ejemplos
  de consultas bien formadas) y *fichas* de los niveles gruesos (día-barrio y flujos entre barrios, ~18 000
  documentos) obtenidas **a través de la API de acceso**, es decir, ya protegidas. Las cifras exactas y el nivel
  hora-zona siguen saliendo de la API por *tool calling*, con las mismas barreras deterministas del chatbot actual.
- **Proveedor:** Helmcode, `https://api.helmcode.com/v1`, infraestructura en la UE y sin registro de prompts.
  Chat `deepseek-v4-flash` (tool calling nativo) o `qwen3.6` con `reasoning_effort=none` (el doble de rápido);
  embeddings `qwen3-embedding` (4096 dimensiones); `rerank` opcional. **Lista blanca** en `llm.py`: los modelos
  que Helmcode revende (claude-*, gpt-*, gemini-*) salen de la UE y se pagan aparte, y están vetados aunque la
  clave los liste.
- **E3.** La regla 9 de `docs/escenario_E3.md` («las preguntas no salen del equipo») deja de cumplirse tal cual: al
  proveedor viajan la pregunta, el historial de la sesión, el contexto recuperado y los agregados protegidos.
  Nunca datos individuales: el chatbot no está en la red `datos` ni tiene credenciales de datos. El Agente 5 lo
  documenta como decisión **matizada** en la bitácora; el chatbot local sigue disponible.
- **Auditoría.** Cliente `chatbot_rag` en la API de acceso (`ACCESO_CLAVE_CHATBOT_RAG`): las decisiones de los dos
  chatbots se distinguen en `auditoria.decisiones`.
- Carpeta `parte3_chatbot_rag/`, servicio `chatbot-rag` (http://localhost:8011), perfiles Compose `rag` y
  `rag-indexar`. Se reutilizan `herramientas.py` (cliente de la API, filtro previo) y `cifras.py` (cifras
  verificadas) del chatbot actual por `PYTHONPATH`, **sin modificarlos**.

## 2. Reglas para no pisarse

1. Rama base `tarea/rag-base`. Cada agente: un *worktree* y una rama a partir de ella, por ejemplo
   `git worktree add ../PIDS-rag-2 -b rag/2-corpus tarea/rag-base`. PRs a `tarea/rag-base`; de ahí un solo PR a `main`.
2. **Propiedad exclusiva de ficheros** (tabla del punto 3). Lo ajeno no se edita: se pide en el PR.
3. **Nadie toca** `parte3_chatbot/`, `parte2_plataforma/`, `config/` ni `tests/test_chatbot.py`. Si hace falta
   cambiar una función compartida, se copia a `parte3_chatbot_rag/` con otro nombre.
4. En `parte3_chatbot_rag/` no se crean módulos con el mismo nombre que los de `parte3_chatbot/` (`agente`,
   `herramientas`, `cifras`, `prompts`, `gestos`, `casos_de_uso`, `bateria_trampa`, `comprobar_agente`): los dos
   directorios comparten `PYTHONPATH`. La única excepción es `app.py`, el punto de entrada de Chainlit.
5. **Solo la carpeta principal del repositorio ejecuta `docker compose`** (un `up` desde otro *worktree* recrea
   servicios con los ficheros de esa carpeta). Los agentes 2-5 prueban desde el anfitrión con `uv run`:
   `ACCESO_URL=http://localhost:8002` y `ACCESO_CLAVE=$ACCESO_CLAVE_CHATBOT_RAG` (o `$ACCESO_CLAVE_EQUIPO`) del
   `.env`, `QDRANT_URL=http://localhost:6333` (Qdrant ya está levantado en la carpeta principal:
   `docker compose --profile rag up -d qdrant`) y las variables `LLM_*` del `.env`.
6. `pyproject.toml` y `uv.lock` solo los toca el Agente 1: si necesitas una librería, pídela. `BITACORA.md`,
   `TAREAS.md`, `README.md` y `docs/` solo el Agente 5: cada agente escribe su párrafo de bitácora en la
   descripción del PR y el 5 lo consolida.
7. Tests sin red ni servicios: `DeterministicFakeEmbedding(size=8)`, `QdrantClient(':memory:')`,
   `GenericFakeChatModel` o `AIMessage(tool_calls=[...])`, y una API falsa (la de `tests/test_chatbot.py`, copiada).
   El CI pasa `uv run pytest` con todos los grupos instalados.
8. Commits y PRs sin menciones a herramientas de IA (regla del repositorio).

## 3. Propiedad de ficheros

| Agente | Tema | Ficheros |
|---|---|---|
| **1** | Infraestructura y proveedor LLM | `pyproject.toml`, `uv.lock`, `.env.example`, `scripts/generar_env.py`, `docker-compose*.yml`, `docker/servicio-python.Dockerfile`, `.dockerignore`, `Makefile`, `.github/workflows/ci.yml`, `README.md` (stack y puesta en marcha; pasó del Agente 5 al 1 el 21/09), `parte3_chatbot_rag/{llm.py,comprobar_llm.py,CONTRATOS.md}`, `tests/{test_rag_llm,test_generar_env}.py` |
| **2** | Corpus, indexación y recuperación | `parte3_chatbot_rag/{corpus.py,fichas.py,indexar.py,recuperador.py}`, `parte3_chatbot_rag/corpus/` (ejemplos y glosario), `tests/{test_rag_corpus,test_rag_recuperador}.py` |
| **3** | Agente RAG (núcleo) | `parte3_chatbot_rag/{agente_rag.py,herramientas_lc.py,prompts_rag.py}`, `tests/test_rag_agente.py` |
| **4** | Interfaz y evaluación | `parte3_chatbot_rag/{app.py,chainlit.md,casos_de_uso_rag.py,bateria_trampa_rag.py,comparar.py}`, `tests/test_rag_evaluacion.py` |
| **5** | Privacidad, guardia de salida y documentación | `parte3_chatbot_rag/{salida.py,README.md}`, `tests/test_rag_salida.py`, `docs/chatbot_rag.md`, `docs/{escenario_E3,comparativa,arquitectura,casos_uso,metricas_calidad}.md`, `BITACORA.md`, `TAREAS.md` (el `README.md` de la raíz ya no: lo lleva el Agente 1) |

## 4. Variables de entorno (ya en `.env.example`; `make entorno-completar` las añade a un `.env` existente)

```
LLM_BASE_URL=https://api.helmcode.com/v1
LLM_API_KEY=                     # a mano, del panel de Helmcode; generar_env no la inventa
LLM_MODELO=deepseek-v4-flash     # o qwen3.6 (con LLM_RAZONAMIENTO=none)
LLM_MODELO_EMBEDDINGS=qwen3-embedding
LLM_TEMPERATURA=0.2
LLM_RAZONAMIENTO=                # opcional: none|minimal|low|medium|high|max (reasoning_effort)
LLM_TIMEOUT_SEGUNDOS=90          # opcional
QDRANT_URL=http://qdrant:6333    # desde el anfitrión: http://localhost:6333
RAG_K=6
RAG_RERANK=false
ACCESO_CLAVE_CHATBOT_RAG=        # la genera make entorno; cliente "chatbot_rag" de la API de acceso
PUERTO_CHATBOT_RAG=8011
PUERTO_QDRANT=6333
```

Dentro de los contenedores `chatbot-rag` y `rag-indexar`: `PYTHONPATH=/app/parte3_chatbot_rag:/app/parte3_chatbot`,
`ACCESO_URL=http://acceso:8000`, `ACCESO_CLAVE=$ACCESO_CLAVE_CHATBOT_RAG`; `docs/` está montado en `/app/docs`
(solo lectura) para el indexador. La raíz del repositorio se localiza con `Path(__file__).resolve().parents[1]`
(`/app` en Docker); `config/` se lee con `PIDS_CONFIG_DIR` (como hace `parte2_plataforma/comun`).

## 5. Contratos

### `llm.py` (Agente 1, hecho)

```python
BASE_URL_POR_DEFECTO, MODELO_POR_DEFECTO, EMBEDDINGS_POR_DEFECTO
MODELOS_UE: frozenset[str]           # deepseek-v4-flash, qwen3.6, gemma4, glm5.3, glm5.3-flash, glm5.2, qwen3-embedding, rerank
DIMENSION_EMBEDDINGS = 4096
LOTE_EMBEDDINGS = 32                 # máximo del endpoint /v1/embeddings (60 peticiones/min)
class ModeloNoPermitido(ValueError); class FaltaClave(RuntimeError)
def modelo_permitido(modelo: str) -> bool
def obtener_llm(temperatura: float | None = None, modelo: str | None = None, razonamiento: str | None = None, **opciones) -> ChatOpenAI
def obtener_embeddings(modelo: str | None = None) -> OpenAIEmbeddings      # check_embedding_ctx_length=False, chunk_size=32
async def modelos_disponibles(cliente: httpx.AsyncClient | None = None) -> list[str]
async def reordenar(pregunta: str, documentos: list[str], top_n: int | None = None, cliente=None) -> list[tuple[int, float]]
def tokens_de(mensaje: AIMessage) -> dict[str, int]   # {'entrada', 'salida', 'razonamiento', 'total'}
def razonamiento_de(mensaje: AIMessage) -> str | None  # hoy siempre None: LangChain no conserva reasoning_content
```

### `recuperador.py` (Agente 2)

```python
COLECCION_CONOCIMIENTO = 'conocimiento'
COLECCION_FICHAS = 'agregados_gruesos'

class Recuperador(Protocol):
    async def recuperar(self, pregunta: str, k: int = 6) -> list[Document]

def obtener_recuperador(colecciones: Sequence[str] = (COLECCION_CONOCIMIENTO, COLECCION_FICHAS),
                        k: int | None = None, rerank: bool | None = None,
                        cliente: QdrantClient | None = None, embeddings: Embeddings | None = None) -> Recuperador
```

`Document.page_content` es el texto que verá el LLM. `Document.metadata`, siempre:
`tipo` (`doc` | `catalogo` | `zona` | `ejemplo` | `ficha`), `fuente` (ruta del fichero o `api:/consultas`), `titulo`.
En las fichas, además, **los mismos campos que la fila de la API**: `nivel`, `dia` (ISO), `barrio_origen`,
`barrio_destino` (solo flujos), `suprimido` (bool), `n_viajes`, `distancia_media`, `importe_medio`,
`propina_media`, `pct_pago_tarjeta` (nulos si el grupo está enmascarado). Con estos metadatos el Agente 3
convierte cada ficha en una fila «vista en el turno» para la barrera de cifras.

Fichas: día-barrio y flujos de todo 2020, **vía `POST /consultas`** con la clave `chatbot_rag`, mes a mes (la
API admite 31 días por consulta) y **barrio a barrio** (trunca a 500 filas). Los grupos suprimidos se indexan
como «enmascarado por privacidad», sin cifra. Texto en español natural con el día de la semana. Colecciones
`cosine` de `DIMENSION_EMBEDDINGS`; `indexar.py` idempotente (id estable por dimensiones) y por lotes de
`LOTE_EMBEDDINGS`, con reintentos (el cliente de OpenAI ya reintenta los 429).

### `agente_rag.py` (Agente 3)

```python
class Guardia(Protocol):                                  # la implementa salida.py (Agente 5)
    def revisar(self, mensajes: list[BaseMessage]) -> list[BaseMessage]   # lanza FugaSalida
    def registrar(self, respuesta: AIMessage) -> None

@dataclass
class TurnoRAG(Turno):                                    # Turno = parte3_chatbot/agente.py, sin cambios
    fuentes: list[dict] = field(default_factory=list)     # [{'titulo', 'fuente', 'tipo'}]

class AgenteRAG:
    def __init__(self, acceso: ClienteAcceso, llm: BaseChatModel, recuperador: Recuperador,
                 guardia: Guardia | None = None, k: int | None = None, max_pasos: int = 5)
    async def responder(self, texto: str, ejecutar: Ejecutor | None = None) -> TurnoRAG
    async def responder_alternativa(self, alternativa: dict, ejecutar: Ejecutor | None = None) -> TurnoRAG
```

Flujo de `responder`: filtro previo reutilizado (`herramientas.parece_individual`, `ClienteAcceso.rechazo_destino`)
→ `recuperador.recuperar()` → prompt con contexto y fuentes → bucle `llm.bind_tools()` con las cuatro
herramientas de `herramientas_lc.py` (`consultar_viajes`, `ultima_hora_con_datos`, `buscar_zona`,
`solicitud_individual`, que delegan en `ClienteAcceso.ejecutar`) → barreras de `cifras.py`. `guardia.revisar()`
antes de cada `ainvoke` y `guardia.registrar()` después. Las fichas recuperadas cuentan como datos del turno para
`cifras_no_justificadas`; si no, el LLM quedaría bloqueado al citarlas. `Turno.bloqueo`, `respuesta`, `llamadas` y
`alternativa` conservan el significado del chatbot actual para que la interfaz y las suites funcionen igual.

### `salida.py` (Agente 5)

```python
class FugaSalida(RuntimeError)
class GuardiaSalida:                                      # cumple el Protocol Guardia
    def __init__(self, max_caracteres: int = 60_000)
    def revisar(self, mensajes: list[BaseMessage]) -> list[BaseMessage]
    def registrar(self, respuesta: AIMessage) -> None     # acumula llm.tokens_de(respuesta) por sesión
    @property
    def tokens(self) -> dict[str, int]
```

`revisar` rechaza campos individuales de `config/privacidad.json` con valor, claves (`sk-`, `X-API-Key`) y
mensajes demasiado largos; registra tokens sin guardar el contenido de la conversación.

### `app.py` (Agente 4)

Construye `AgenteRAG(ClienteAcceso(), obtener_llm(), obtener_recuperador(), guardia=GuardiaSalida())` en
`on_chat_start`; muestra los pasos de las herramientas, el botón de la alternativa y un desplegable «Fuentes» con
`turno.fuentes`. `casos_de_uso_rag.py` y `bateria_trampa_rag.py` leen `parte3_chatbot/preguntas_trampa.json` y
usan los detectores de `cifras.py`; salida en `informes/chatbot_rag/` (no se versiona).

## 6. Qué hace cada agente y cuándo está hecho

- **Agente 1** (hecho salvo la integración final): dependencias, `.env`, Compose, Makefile, CI, `llm.py`,
  `comprobar_llm.py` y tests. Hecho cuando `make test`, `docker compose config` con todos los perfiles y
  `make rag-comprobar` pasan. Pasan.
- **Agente 2**: `corpus.py`, `fichas.py`, `indexar.py`, `recuperador.py`, `corpus/ejemplos.json` (20-30 pares
  pregunta → llamada correcta a `consultar_viajes`). Hecho cuando los tests con Qdrant `:memory:` pasan y, contra la
  plataforma, `make rag-indexar` termina y «¿qué zonas hay en el aeropuerto?» recupera JFK, LaGuardia y Newark.
- **Agente 3**: `herramientas_lc.py`, `agente_rag.py`, `prompts_rag.py`. Hecho cuando los tests con LLM y
  recuperador falsos cubren: filtro previo, tool call → cifra verificada, cifra inventada → tablas, todo
  enmascarado → sin LLM, ficha citada → permitida, guardia que lanza `FugaSalida`.
- **Agente 4**: `app.py`, `chainlit.md`, `casos_de_uso_rag.py`, `bateria_trampa_rag.py`, `comparar.py`. Hecho
  cuando las suites corren contra el agente real y hay una tabla Ollama frente a RAG (21 ejecuciones de casos y
  105 de la batería).
- **Agente 5**: `salida.py` y tests; `docs/chatbot_rag.md`; regla 9 matizada en `escenario_E3.md`; fila nueva en
  `comparativa.md`; componentes y puertos en `arquitectura.md`; resultados de M1 del chatbot RAG en
  `casos_uso.md` y `metricas_calidad.md`; README; T13 en `TAREAS.md`; entrada de `BITACORA.md` con la decisión.

## 7. Orden e integración

```
Fase 0  Agente 1: tarea/rag-base (hecho)
Fase 1  Agente 2 ‖ Agente 3 ‖ Agente 5 ‖ Agente 4 (interfaz contra un agente falso hasta que aterrice el 3)
Fase 2  Fusión en tarea/rag-base en orden 2 → 3 → 5 → 4
        make sync && make test && make test-spark
        make chatbot-rag && make rag-indexar && make rag-casos && make rag-bateria
        Agente 5 cierra la bitácora → PR tarea/rag-base → main
```

Hasta que exista `app.py`, `make chatbot-rag` levanta Qdrant pero el contenedor `chatbot-rag` no arranca; para
probar el proveedor vale `make rag-comprobar`.

Estado el 21/09 por la tarde: `rag/3-agente` (terminada) y `rag/4-interfaz` (en curso) se crearon desde `main`, no
desde `tarea/rag-base`, pero solo añaden ficheros propios, así que se fusionan limpias. Los agentes 2 y 5 siguen
trabajando. El `README.md` de la raíz ya recoge el chatbot RAG (stack, puesta en marcha, puertos y estructura).

## 8. Comprobado contra la API real (21/09/2026)

- `/v1/models` lista 19 modelos; los revendidos devuelven 402 con esta clave y, en cualquier caso, `llm.py` los veta.
- Chat con `deepseek-v4-flash`: «listo» en 1,8-2,2 s; el razonamiento llega aparte (`reasoning_content`) y no se
  cuela en `content`; `usage_metadata` trae los tokens de razonamiento.
- Tool calling con el esquema real de `consultar_viajes`: `nivel=hora_zona`, `desde=2020-01-15T08:00:00`,
  `hasta=2020-01-15T12:00:00`, `zona_origen="JFK"`, y usa el total del resumen (652) en la respuesta.
  Con `qwen3.6` y `reasoning_effort=none`, lo mismo en ~1 s.
- Embeddings: 4096 dimensiones, 0,9 s por lote; límites 60 peticiones/min y 32 textos por petición.
- Rerank (`POST /v1/rerank`, `{"model": "rerank", "query", "documents", "top_n"}`): devuelve
  `results[{index, relevance_score}]`; los dos aeropuertos quedan primeros.
- Límites del chat: 100 peticiones/min, 10 simultáneas (5 en qwen3.6 y gemma4), 2M tokens/min por clave.

## 9. Riesgos conocidos

- `OpenAIEmbeddings` sin `check_embedding_ctx_length=False` tokeniza con tiktoken y el proveedor rechaza la petición
  (ya resuelto en `llm.py`).
- Las cifras de las fichas quedan congeladas en el índice: tras recargar el histórico hay que reindexar.
- La barrera de cifras verificadas necesita que las fichas recuperadas cuenten como datos del turno (Agente 3).
- Las baterías disparan la alerta de Grafana de consultas rechazadas, como con el chatbot actual.
- La clave de Helmcode solo vive en `.env`; si se comparte, se rota en el panel del proveedor.
