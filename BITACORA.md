# Bitácora del proyecto

Registro de cambios escrito por personas, no por Git. Sirve para dos cosas:

1. Que cualquiera del equipo sepa qué ha pasado sin leerse el código ni los commits.
2. Que cualquier asistente de IA que retome el trabajo tenga el contexto al día y no reinvente ni
   deshaga lo ya decidido.

## Cómo se usa

- **Antes de trabajar:** lee «Estado actual», «Decisiones tomadas» y las dos o tres últimas entradas,
  y mira qué toca en [`TAREAS.md`](TAREAS.md). Si vas a usar una IA, dale los dos ficheros completos
  como primer contexto.
- **Al terminar, antes del commit o del *pull request*:** añade una entrada nueva **arriba** de la
  lista, actualiza «Estado actual» y marca la tarea en [`TAREAS.md`](TAREAS.md).
- **Si has trabajado con una IA:** la entrada la firma la persona que ha usado y revisado el
  resultado. En el repositorio solo figuramos los cinco del grupo como autores: nada de
  `Co-Authored-By` ni firmas automáticas (`make hooks` las quita; el CI «Autoría» las rechaza). Ver
  [`docs/repositorio.md`](docs/repositorio.md) y [`AGENTS.md`](AGENTS.md).
- **Si cambias una decisión anterior:** añádela a «Decisiones tomadas» y marca la vieja como
  *sustituida*, explicando por qué. No borres entradas antiguas: esto se escribe añadiendo.
- **Si dejas algo a medias:** dilo en «Pendiente y riesgos». Es la parte más útil para quien siga.
- **Nunca** escribas aquí contraseñas, claves ni rutas con datos personales.

## Estado actual

**Última actualización: 22/09/2026 · Javier Saguar** (TAXI AI como botón y panel en todas las páginas del portal)

| | |
|---|---|
| **Escenario** | E3 · privacidad total |
| **Funciona y está probado en ejecución** | Núcleo (S3, Redpanda, MongoDB, APIs), carga histórica con Spark en modo cluster y supresión complementaria, tiempo real con streaming, filtro de privacidad (permitida / enmascarada / rechazada), DAG de Airflow, Prometheus (9 objetivos), panel de Grafana con 3 alertas probadas, informe de auditoría, chatbot de Ollama con barreras sobre las cifras y **chatbot RAG** (LangChain + Qdrant + LLM externo en la UE) con las mismas barreras y una guardia de salida. 340 tests de Python y 17 de Scala |
| **Datos cargados** | Año 2020 completo, recargado el 21/09 con supresión complementaria: 23 684 852 viajes válidos; 287 003 grupos hora-zona publicados (430 126 ocultos). Índice de Qdrant: 376 documentos de conocimiento y 18 187 fichas de agregados gruesos |
| **Métricas** | M1: 0 fugas en la API (31 casos), en el chatbot de Ollama (105 ejecuciones) y en el chatbot RAG (105 ejecuciones) · M2: con k = 10 se publica el 95,1 % de los viajes en hora-zona · M3: p95 35,4 s (objetivo < 60 s) |
| **Chatbots** | Ollama: `llama3.1:8b` en GPU a temperatura 0,2, 21/21 casos en 2-3 s · RAG: `deepseek-v4-flash` (Helmcode, UE), 21/21 casos con p50 1,1 s y unos 6 000 tokens por pregunta. Detalle en `docs/chatbot_rag.md` |
| **Parte 1** | Se ejecuta desde el repositorio, con `PIDS_DATOS` apuntando a las imágenes (que siguen fuera de Git) |
| **Portal web (parte 4)** | En `main` y levantado (`make frontend`, http://localhost:8020, contraseña `FRONTEND_CLAVE` de `.env`): panel, explorador, tiempo real, privacidad y auditoría, operaciones y documentación, y el asistente TAXI AI (Ollama y RAG) como botón fijo con panel derecho en todas las páginas (T16). Demostración pública en Vercel con datos grabados (`parte4_frontend/demo`). 429 tests de Python, 17 de Scala y 139 de Vitest |
| **Sin empezar** | Alta disponibilidad (T09), vídeo y presentación (T10). De T06 queda el vídeo con la webcam |
| **Cómo levantarlo** | En Ubuntu (WSL2), paso a paso en el README («Puesta en marcha»): `make entorno`, pegar `LLM_API_KEY`, `make sync && make test`, `make construir && make todo`, `make historico-muestra` y `make rag-indexar`; cada día, `make todo` y `make tiempo-real` |
| **Forma de trabajar** | Una rama por persona (tabla en el README) y cambios a `main` por *pull request*. Para trabajo en paralelo, una rama de tarea con contratos por bloque (`parte3_chatbot_rag/CONTRATOS.md`). Cada copia, con `make hooks`; el CI «Autoría» rechaza coautorías y firmas automáticas |
| **Repositorio** | Recreado en GitHub el 22/09/2026 (mismo nombre) para eliminar una coautoría ajena al grupo: [`docs/repositorio.md`](docs/repositorio.md). Copias anteriores: sincronizar con `git reset --hard origin/main`. **Vercel (`happytaxi`, `yellowveil`) hay que volver a conectarlo al repositorio nuevo** (§4 de ese documento) |
| **Siguientes tareas** | Ver [`TAREAS.md`](TAREAS.md) |
| **Pendiente inmediato** | Grabar el vídeo de T06 en Windows (el ciclo ya responde a 👍 y ✋). Confirmar en grupo la decisión del LLM externo (regla 9 de E3), dejar el tiempo real listo para la demo (T11) y subir la copia del dataset de gestos, ya hecha y verificada (T01) |
| **Requisitos** | Todo instalado en este equipo (incluido el NVIDIA Container Toolkit). En equipos sin GPU: `make chatbot SIN_GPU=1` con `OLLAMA_MODELO=llama3.2:3b`, o el chatbot RAG, que no necesita GPU |

## Decisiones tomadas

| Fecha | Decisión | Motivo | Quién | Estado |
|---|---|---|---|---|
| 17/09/2026 | Escenario **E3 (privacidad total)** | La demo luce y encaja con la parte 1, que ya procesa en el dispositivo por privacidad | Equipo | Vigente |
| 17/09/2026 | Stack: Docker Compose, Redpanda, Spark 4 en Scala (modo cluster), MongoDB + S3, FastAPI, Airflow, Grafana + Prometheus, Ollama local + Chainlit | Ver `docs/comparativa.md` | Equipo | Vigente |
| 17/09/2026 | **SeaweedFS** como almacenamiento S3 en lugar de MinIO | MinIO retiró sus imágenes de Docker Hub (última publicada en 2025) | Javier Saguar | Vigente |
| 17/09/2026 | Las reglas de validación y privacidad viven en `config/*.json`, compartidas por Python y Scala | E3 exige la misma protección en histórico y tiempo real; así no se duplican | Javier Saguar | Vigente |
| 17/09/2026 | El trabajo se hace dentro de WSL2 (Ubuntu) con Docker; la parte 1 sigue en Windows | Las herramientas son de Linux y la webcam solo va bien en Windows | Equipo | Vigente |
| 17/09/2026 | La integración gestos ↔ chatbot es la última fase | Es opcional en el enunciado (diapositiva 5) | Equipo | Vigente |
| 21/09/2026 | Supresión complementaria en la carga histórica (en tiempo real, todavía no) | El ataque por diferencia revelaba 779 grupos suprimidos; mitigarlo cuesta menos del 0,04 % de los viajes | Javier Saguar | Vigente |
| 21/09/2026 | Mantener k = 10 | Es el codo de la curva privacidad-utilidad (M2) | Javier Saguar | Propuesta: confirmar en grupo |
| 21/09/2026 | En el chatbot, cada cifra tiene que salir de los datos del turno; LLM a temperatura 0,2 | Barrera determinista contra cifras inventadas o deducidas; con 0,2 acierta más y responde antes | Javier Saguar | Vigente |
| 21/09/2026 | Una rama por persona y cambios a `main` por *pull request* | No pisarnos el trabajo | Javier Saguar | Vigente |
| 21/09/2026 | **Segundo chatbot con LLM externo** (Helmcode, API compatible con OpenAI en la UE y sin registro de prompts) y RAG con Qdrant; el de Ollama se conserva | Modelo mayor sin depender de la GPU y con contexto recuperado; solo viajan la pregunta y agregados ya protegidos, con lista blanca de modelos UE y guardia de salida. Matiza la regla 9 de E3 («las preguntas no salen del equipo»), que sigue cumpliéndose con el chatbot de Ollama | Javier Saguar | Propuesta: confirmar en grupo |
| 21/09/2026 | Trabajo en paralelo por bloques con contratos escritos (`CONTRATOS.md`: propiedad de ficheros y firmas) y una rama de integración `tarea/rag-base` | Cinco bloques a la vez sin conflictos: las tres ramas se fusionaron limpias | Javier Saguar | Vigente |
| 22/09/2026 | La regla de autoría se hace cumplir con un hook `commit-msg` y un CI «Autoría»; ningún commit lleva `Co-Authored-By` (ni entre miembros) | Una coautoría automática llegó a `main` en el PR #1 y solo se pudo quitar recreando el repositorio | Javier Saguar | Vigente |

## Plantilla (copiar y rellenar)

```markdown
### AAAA-MM-DD · Nombre Apellido · título corto del cambio

- **Rama / commits:** `nombre-rama` · `abc1234`
- **Qué he hecho:**
  -
- **Por qué:** (qué problema resuelve o qué parte del enunciado cubre)
- **Ficheros clave:** `ruta/fichero.py`, `ruta/otro.scala`
- **Cómo comprobarlo:**
  ```bash
  make test
  ```
- **Resultado:** (tests que pasan, capturas, cifras medidas)
- **Pendiente y riesgos:** (lo que queda, lo que puede romperse, lo que no he podido probar)
- **Contexto para quien siga:** (decisiones implícitas, trampas, por qué NO se hizo de otra forma)
```

---

## Entradas

### 2026-09-22 · Javier Saguar · T16 · TAXI AI: el asistente como botón fijo y panel derecho, no como sección

- **Rama / commits:** `tarea/taxi-ai` · un commit
- **Qué he hecho:**
  - «Asistente» ya no está en el menú izquierdo ni tiene ruta: `SECCIONES` pasa de siete a seis y `/asistente` redirige a
    la portada con el panel abierto (para los enlaces antiguos).
  - Botón fijo «TAXI AI» en la esquina inferior derecha (`componentes/shell/BotonTaxiAI.tsx`), en todas las páginas del
    portal. Al pulsarlo, el panel (`componentes/shell/PanelAsistente.tsx`, 30 rem, todo el alto) entra desde el borde
    derecho con el mismo chat de antes (`paginas/asistente/Asistente.tsx`, el antiguo `PaginaAsistente` adaptado a una
    columna). El botón se desplaza a la izquierda del panel y pasa a «Cerrar»; en pantallas estrechas el panel ocupa todo
    el ancho y el botón se esconde (queda la X del panel). Escape también lo cierra.
  - Cerrar el panel solo lo esconde: no navega, y la conversación y la sesión del BFF siguen vivas (se comprueba en los
    tests). El chat se monta la primera vez que se abre, así que quien no lo usa no abre ninguna sesión en el BFF.
  - Accesibilidad: el panel es una región `aside` con nombre, `aria-hidden` e `inert` cuando está cerrado; el foco va al
    cuadro de texto al abrir (o al panel si aún no se puede escribir) y vuelve al botón al cerrar; `aria-expanded` y
    `aria-controls` en el botón.
- **Por qué:** T16: el asistente es un acceso del producto, no otra página; tiene que estar a mano desde cualquier sección.
- **Ficheros clave:** `parte4_frontend/web/src/componentes/shell/{AppShell,BotonTaxiAI,PanelAsistente,navegacion}.ts(x)`,
  `parte4_frontend/web/src/paginas/asistente/Asistente.tsx`, `parte4_frontend/web/src/rutas.tsx`
- **Cómo comprobarlo:**
  ```bash
  cd parte4_frontend/web && npm run lint && npm test -- --run && npm run build
  make frontend        # y en http://localhost:8020, desde cualquier sección, el botón TAXI AI abajo a la derecha
  ```
- **Resultado:** 139 tests de Vitest en verde (4 nuevos en `AppShell.test.tsx`; los del asistente abren el panel con el
  botón). Probado con Chromium sin cabeza contra el BFF real: menú con seis secciones; botón en la esquina; panel de
  480 px a la derecha sin cambiar la URL; sigue abierto al pasar a otra sección; Escape lo cierra y el botón vuelve a su
  sitio; `/asistente` → `/` con el panel abierto; sin desbordamiento horizontal; a 600 px el panel ocupa el ancho y el
  botón se oculta; una pregunta real a Ollama desde el panel («Manhattan con 203,866 viajes», 2,3 s) que sigue ahí tras
  cerrar y reabrir desde otra sección. Sin errores de consola.
- **Pendiente y riesgos:** la imagen del portal (`make frontend`) hay que reconstruirla para que salga el cambio; la
  demostración de Vercel también. El panel no es modal (la página sigue usable detrás): es intencionado.
- **Contexto para quien siga:** el estado abierto/cerrado vive en `AppShell` (persiste entre rutas porque el shell no se
  desmonta); el panel no usa el `Sheet` de shadcn porque ese desmonta el contenido al cerrar y perdería la conversación.
  Las clases de Tailwind del desplazamiento del botón (`right-[31.5rem]`) van escritas literales: Tailwind no genera
  clases construidas en tiempo de ejecución.

### 2026-09-22 · Javier Saguar · Repositorio recreado en GitHub y barreras de autoría

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - El PR #1 (rediseño del portal, de Alejandro Cuevas) trajo a `main` un commit con una coautoría y una firma
    automáticas de una herramienta, que GitHub mostraba como contribuidora. Reescribí el commit y el *merge* sin
    el trailer y con el mismo código, autor y fecha (`fa9036a → 6785183`, `7ea22c9 → 095b340`) y los subí
    forzados. GitHub seguía mostrándola por la referencia del PR, que no se puede borrar.
  - Copia completa en mi equipo (`~/copias/PIDS-Proyecto1-20260922-0051`), borrado del repositorio, creación de
    uno nuevo con el mismo nombre, subida de las 9 ramas limpias y nuevas invitaciones a los cuatro compañeros.
    GitHub ya no encuentra el commit antiguo y los contribuidores son solo del grupo.
  - Para que no vuelva a pasar: hook `commit-msg` que quita esas líneas (`make hooks`, también en `make sync`),
    CI «Autoría» que revisa commits y descripción de los PR, `scripts/comprobar_autoria.py` con sus tests,
    `AGENTS.md` para los asistentes y `docs/repositorio.md` con la incidencia y cómo recuperarse.
- **Por qué:** es la regla principal del grupo: en el repositorio solo figuramos los cinco como autores.
- **Ficheros clave:** `docs/repositorio.md`, `AGENTS.md`, `scripts/comprobar_autoria.py`, `.githooks/commit-msg`,
  `.github/workflows/autoria.yml`, `tests/test_autoria.py`, `Makefile` (`hooks`)
- **Cómo comprobarlo:**
  ```bash
  make hooks && make test
  python3 scripts/comprobar_autoria.py --rango main
  ```
- **Resultado:** historial de todas las ramas sin coautorías; tests de autoría en verde.
- **Pendiente y riesgos:** **volver a conectar Vercel** (`happytaxi` y `yellowveil`) al repositorio nuevo; que
  los compañeros acepten la invitación, sincronicen su copia (`git reset --hard origin/main`) y ejecuten
  `make hooks`. Se perdieron el PR #1 y el historial del CI. El hook se puede saltar con `--no-verify`: el
  CI es la barrera que no se salta.
- **Contexto para quien siga:** una copia anterior al 22/09 que se suba vuelve a colar el commit antiguo
  (`docs/repositorio.md` §4 explica cómo detectarlo). Los hashes anteriores a `235ddc2` no cambiaron.

### 2026-09-22 · Javier Saguar · T08 · Servicios sin login fuera del anfitrión y modelo de amenazas

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Dejé de publicar Kafka, la consola de Redpanda, la interfaz de Spark y sus workers, Prometheus,
    Ollama y Qdrant. No tienen credencial. Siguen usándose por el nombre del contenedor.
  - Los dos chatbots de Chainlit piden `CHATBOT_USUARIO` / `CHATBOT_CLAVE`. La sesión la firma
    `CHAINLIT_AUTH_SECRET`.
  - `make entorno FORZAR=1` regenera `.env`. GNU make no acepta `make entorno --forzar`.
  - Escrito [`docs/seguridad.md`](docs/seguridad.md).
- **Por qué:** T08. En `127.0.0.1` se podía leer la interfaz de Spark, Prometheus, Qdrant y Ollama sin
  clave, y Kafka (`19092`) aceptaba conexiones hacia `viajes-crudos`.
- **Ficheros clave:** `docker-compose.yml`, `docs/seguridad.md`, `parte3_chatbot/app.py`,
  `parte3_chatbot_rag/app.py`, `Makefile`
- **Cómo comprobarlo:**
  ```bash
  uv run pytest tests/test_publicacion.py tests/test_generar_env.py -q
  make entorno FORZAR=1    # solo si se van a recrear los volúmenes de Mongo, Airflow y Grafana
  ```
- **Resultado:** los puertos 8090, 8091, 8092, 9090, 6333, 11435, 19092, 6066 y 8088 no aceptan
  conexión en el anfitrión. La pasarela 6066 sí responde desde Airflow (`spark-master:6066`). Login del
  chatbot: clave mala 401, clave buena 200 (8010 y 8012). Grafana sin sesión 401, S3 sin clave 403,
  consultas sin clave 401. MongoDB de prueba con `01_usuarios.js`: sin borrar el volumen sigue valiendo
  la contraseña vieja; con el volumen nuevo solo la nueva, y sin contraseña `listDatabases` da 13.
  El trabajo `pids-tiempo-real` se relanzó después de recrear el máster.
- **Pendiente y riesgos:** `/salud`, `/metrics` y `/docs` de las APIs siguen sin clave (no llevan viajes).
  `make frontend-dev` ya no alcanza Prometheus, Ollama ni Qdrant. No he recreado los volúmenes reales:
  eso borraría los agregados del año 2020.
- **Contexto para quien siga:** la rotación de verdad es `make entorno FORZAR=1` y luego
  `docker volume rm pids_mongo-datos pids_airflow-db pids_grafana-datos`. S3 no necesita borrar su volumen.

### 2026-09-22 · Javier Saguar · T06 (en curso) · La demo de gestos confirma y cancela consultas del chatbot

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - `demo-gestures-PIDS.py` llama a `EmisorGestos.observar` en cada predicción (cada 0,25 s, y al soltar la mano).
    Solo si existe `PIDS_CLAVE_GESTOS`; sin esa variable la demo de la parte 1 no cambia.
  - `GESTOS_ACTIVOS=true` en `.env` y chatbot recreado. 👍 ejecuta la alternativa pendiente y ✋ la cancela,
    con el mismo aviso que el botón.
  - La sesión de Chainlit se vuelve a fijar al llegar el SSE: el gesto no se procesa en la tarea del chat.
- **Por qué:** es la caja «Integración» de la diapositiva 5. El rechazo con alternativa ya existía; faltaba
  que el gesto de la parte 1 hiciera lo mismo que el botón.
- **Ficheros clave:** `parte1_gestos/demo/src/demo-gestures-PIDS.py`, `integracion/cliente_gestos.py`,
  `parte3_chatbot/app.py`
- **Cómo comprobarlo:**
  ```bash
  uv run pytest tests/test_cliente_gestos.py -q
  # con el chatbot levantado, el mismo POST que envía la demo:
  python integracion/cliente_gestos.py --clave "$CAPTURA_CLAVE_GESTOS" --gesto thumbsup
  ```
  En Windows, con la plataforma en WSL: `$env:PIDS_CLAVE_GESTOS` y la demo. 👍 tras un rechazo individual.
- **Resultado:** 6 tests del anti-rebote. Ciclo real contra el chatbot: una petición individual se rechaza,
  `thumbsup` lanza la alternativa (Times Square, 15/01/2020, 3:00-4:00: 54 viajes, consulta permitida) y
  `paper` responde «consulta cancelada».
- **Pendiente y riesgos:** el vídeo con la webcam no está. Desde WSL no hay cámara (la parte 1 va en Windows).
  El gesto se envía tras ~1 s de la misma predicción (4 veces × 0,25 s) y no se repite en 3 s.
- **Contexto para quien siga:** `paper` es ✋ (cancelar) y `thumbsup` es 👍. `GESTOS_ACTIVOS` se lee al arrancar
  el proceso: hay que recrear el contenedor. El cliente solo manda etiqueta y confianza.

### 2026-09-21 · Javier Saguar · T14 · Portal web en `main`, levantado, y demostración pública en Vercel

- **Rama / commits:** `main` · fusiones de `tarea/frontend` y `tarea/frontend-demo` y el commit de esta entrada
- **Qué he hecho:**
  - Fusionado el portal en `main` (solo chocaba la bitácora) y levantado desde la carpeta principal:
    `make entorno-completar` (añade `ACCESO_CLAVE_FRONTEND`, `FRONTEND_CLAVE`, `FRONTEND_SECRETO` y `PUERTO_FRONTEND`
    sin tocar el resto), `acceso` recreado para que conozca al cliente `frontend` y `make frontend`.
  - **Vercel** fallaba con «No FastAPI entrypoint found»: construye la raíz, ve `pyproject.toml` y cree que es una
    app FastAPI. Lo que proponía (`[tool.vercel] entrypoint = "parte2_plataforma.acceso.app:app"`) habría publicado en
    internet la API de acceso, la puerta de privacidad, y además no funcionaría sin MongoDB. `vercel.json` fija el
    *framework* en Vite y publica el portal en **modo demostración**: la misma SPA con un sustituto del BFF en el
    navegador que contesta con una instantánea grabada de la plataforma (agregados ya enmascarados por la API, estado,
    auditoría y conversaciones del agente de Ollama). El filtro de privacidad de la API está portado a TypeScript con
    `config/privacidad.json` y se compara con 25 respuestas reales de la API. Detalle en `parte4_frontend/demo/README.md`.
  - La imagen del portal no construía con el modo demostración dentro: la etapa de la SPA solo copiaba
    `parte4_frontend/web` y `src/demo` importa `config/privacidad.json`. Ahora reproduce la estructura del repositorio
    y quita `dist/demo`, que el portal real no necesita.
  - README: «Puesta en marcha» reescrita (primera vez, cada día, usuarios y contraseñas de cada herramienta, portal
    real y demostración). Capturas del portal con datos reales en `docs/capturas/portal_*.png`.
- **Por qué:** cerrar la parte 4 (T14) y que el despliegue de Vercel deje de fallar sin exponer nada de la plataforma.
- **Ficheros clave:** `vercel.json`, `parte4_frontend/demo/`, `parte4_frontend/web/src/demo/`,
  `parte4_frontend/web/vite.demo.config.ts`, `parte4_frontend/bff/Dockerfile`, `README.md`
- **Cómo comprobarlo:**
  ```bash
  make test && make test-frontend
  make frontend                     # http://localhost:8020, contraseña: grep '^FRONTEND_CLAVE=' .env
  cd parte4_frontend/web && npx vite build --config vite.demo.config.ts && npx vite preview --config vite.demo.config.ts
  ```
- **Resultado:** 429 tests de Python y 132 de Vitest en verde, lint y los dos *builds* limpios. Portal en el
  contenedor: sin sesión 401, contraseña mala 401, buena 204; panel, tiempo real, auditoría, Airflow y catálogo
  responden; una consulta con `matricula` da 403; la auditoría registra al cliente `frontend`; el asistente contesta
  con Ollama (9,5 s) y con RAG (96 s ese momento, lentitud del proveedor). La demostración: las siete secciones sin
  errores de consola, y el *build* de Vercel simulado desde un clon limpio con los comandos de `vercel.json`.
- **Pendiente y riesgos:**
  - El tiempo real del portal marca «sin datos recientes» hasta que el *streaming* vuelva a recibir viajes (T11).
  - En pantallas de móvil la barra lateral no se pliega y estrecha el contenido.
  - La instantánea de la demostración es del 21/09; se regraba con `uv run python -m parte4_frontend.demo.instantanea`.
- **Contexto para quien siga:** Vercel no puede llegar a la plataforma (está en Docker en un portátil y la API no se
  publica), por eso la demostración no tiene servidor. No añadir `[tool.vercel]` a `pyproject.toml`.

### 2026-09-21 · Javier Saguar · T01 (en curso) · Copia de seguridad del dataset de gestos

- **Rama / commits:** `main`
- **Qué he hecho:**
  - `dataset_gestos_PIDS_2026-09-16.zip` (598,9 MiB) con las 5 tomas completas (p1 a p5, 3000 imágenes y
    sus `metadata.json`), un `LEEME.txt` y `MANIFIESTO.sha256` con el SHA-256 de cada fichero. Está en
    `C:\Users\Javier\PIDS_HandPose\copias`, junto a su `.sha256`.
  - Quedan fuera las cuatro tomas interrumpidas o vacías (0, 6, 0 y 0 imágenes), que el entrenamiento tampoco
    usa.
  - Sección «Copia de seguridad del dataset» en `parte1_gestos/README.md`: qué contiene, su SHA-256 y cómo
    comprobarla y usarla con `PIDS_DATOS`.
- **Por qué:** las imágenes solo existían en el disco del portátil y el dataset no se puede volver a grabar.
- **Ficheros clave:** `parte1_gestos/README.md`, `TAREAS.md`
- **Cómo comprobarlo:** descargar la copia, comprobar el SHA-256 del README, descomprimir y
  `preprocesar.py` con `PIDS_DATOS` apuntando a su `data`.
- **Resultado:** descomprimida en otra carpeta, los 3005 ficheros coinciden con el manifiesto, y
  `preprocesar.py` desde una copia limpia del repositorio da lo mismo que sobre el original: 5 tomas
  completas, 3000 imágenes, 2931 con mano (97,7 %).
- **Pendiente y riesgos:** subirla a un sitio compartido solo con el grupo (Drive u OneDrive de la UPM),
  anotar el enlace en el README y que otra persona reproduzca el preprocesado desde la copia; hasta entonces la
  copia sigue en el mismo disco que el original.
- **Contexto para quien siga:** son fotos de las cinco personas del grupo: ni en GitHub (el repositorio es
  público) ni con un enlace abierto a cualquiera. El zip va sin compresión porque las JPEG no ganan nada y así
  se abre más rápido.

### 2026-09-21 · Javier Saguar · Portal web corporativo (parte 4): SPA de React y BFF de FastAPI

- **Rama / commits:** `tarea/frontend` · `d5bf245` (contratos), `fc78ef2` (fase 0), `bc52f17` (fase 1) y el de esta entrada
- **Qué he hecho:**
  - Un portal web que reúne en una sola aplicación lo que estaba repartido entre Chainlit, Grafana, Airflow y los
    `/docs` de las APIs: panel (último día publicado por barrio, decisiones de 24 h, frescura del *streaming*, estado de
    servicios), explorador de agregados (tres niveles, zona con buscador, tabla ordenable, gráficos y matriz de flujos,
    rechazos con su alternativa relanzable), asistente (el mismo agente de la parte 3 con pasos en directo por SSE,
    fuentes y tokens; motor Ollama o RAG), tiempo real, privacidad (reglas E3 y auditoría con filtros), operaciones
    (cargas de Airflow y simulador) y documentación.
  - Arquitectura: un contenedor `frontend` (perfil `frontend`, 8020) con un BFF de FastAPI que guarda todas las
    claves y sirve la SPA construida; entrada con una contraseña única (`FRONTEND_CLAVE`) y cookie firmada. Todas las
    cifras pasan por `POST /consultas` de la API de acceso como cliente `frontend` (misma protección, misma auditoría);
    el panel y el tiempo real solo suman grupos visibles. MongoDB solo se lee con `pids_auditor`.
  - Trabajo en paralelo con cinco bloques y propiedad exclusiva de ficheros, fijado en
    `parte4_frontend/CONTRATOS.md` (formas JSON, códigos, variables, rutas, sistema de diseño): F0 cimientos, F1 BFF de
    plataforma, F2 BFF de chat, F3 páginas de datos, F4 asistente y administración. La fase 0 dejó creados los routers y
    páginas vacíos que los demás rellenaron, así nadie tocó ficheros compartidos.
  - Tests sin red: la API de acceso falsa de los tests del BFF aplica el filtro de privacidad real; la SPA se prueba con
    Vitest y una API simulada. Imagen multi-stage (node → python) construida y comprobada.
- **Por qué:** «visualización» y «acceso» del enunciado con un acabado de producto, y un único sitio para la demo;
  además cubre la caja de seguridad (el navegador nunca ve una clave) sin relajar E3.
- **Ficheros clave:** `parte4_frontend/{CONTRATOS,README}.md`, `parte4_frontend/bff/`, `parte4_frontend/web/src/`,
  `tests/test_frontend_bff_{base,plataforma,chat}.py`, `docker-compose.yml` (servicio `frontend`), `Makefile`,
  `.env.example`, `.github/workflows/ci.yml`
- **Cómo comprobarlo:**
  ```bash
  make test-frontend                                   # BFF + SPA sin servicios
  make frontend-dev                                    # BFF en el host; cd parte4_frontend/web && npm run dev
  make frontend                                        # imagen y contenedor: http://localhost:8020 (FRONTEND_CLAVE de .env)
  ```
- **Resultado:** 306 tests de Python (217 + 89 del BFF) y 98 de Vitest en verde; lint y build limpios. Contra la
  plataforma real desde el host: catálogo, consultas (Manhattan 203 866 el 3/3; 403 con alternativa), panel del
  31/12/2020 (41 015 viajes visibles, 2 grupos enmascarados no sumados), tiempo real, auditoría (33 305 decisiones en
  24 h), ejecuciones de Airflow, chat con Ollama (652 viajes de JFK; rechazo → alternativa → 54 viajes) y 200 viajes
  simulados; la imagen `pids/frontend:local` construye en 6 s con caché.
- **Pendiente y riesgos:**
  - Abrir el PR `tarea/frontend` → `main` y, al levantarlo desde la carpeta principal, recrear `acceso` para que conozca
    la clave `frontend` (`ACCESO_CLAVE_FRONTEND` en `.env`: `make entorno` no completa un `.env` existente en esta rama;
    en `tarea/rag-base` sí hay `--completar`). Hasta entonces el BFF en el host usa la clave del equipo.
  - `README.md`, `BITACORA.md`, `TAREAS.md` y `pyproject.toml` también cambian en `tarea/rag-base`: conflictos
    pequeños y aditivos al fusionar.
  - El motor RAG del asistente (tras traer `main` a la rama) corre dentro del BFF con las claves del portal: probado
    desde el host; en el contenedor necesita `LLM_API_KEY` en `.env` y Qdrant indexado.
  - La contraseña del portal es única (sin usuarios ni roles) y la sesión no caduca al cerrar el navegador (12 h).
- **Contexto para quien siga:** cada sección de la SPA vive en su carpeta de `paginas/` y cada endpoint en su fichero de
  `bff/rutas/` + `bff/servicios/`; los tipos de la API están en `web/src/api/tipos.ts` y son el contrato. Los servicios
  opcionales caídos se muestran como «no disponible», nunca rompen la página. Las cachés del BFF (10 min catálogo, 60 s
  panel, 20 s tiempo real) existen para que el refresco automático no multiplique la auditoría.

### 2026-09-21 · Javier Saguar · Chatbot RAG con LLM externo: LangChain, Qdrant y Helmcode, en cinco bloques

- **Rama / commits:** `tarea/rag-base` · `0603ee2` (base), `7c17bb5` (README), fusiones de `rag/2-corpus`,
  `rag/3-agente` y `rag/4-interfaz`, y el cierre (guardia de salida, documentación y mediciones)
- **Qué he hecho:**
  - **Base (bloque 1):** grupo de dependencias `rag` (LangChain 1.4, langchain-openai, langchain-qdrant, qdrant-client
    1.19, openai 3.13; todo con al menos una semana publicado), variables `LLM_*`/`RAG_*` y `make entorno-completar`
    (añade lo nuevo a un `.env` existente y deja `LLM_API_KEY` para pegarla a mano), servicios `qdrant`, `chatbot-rag`
    (8011) y `rag-indexar` en Compose (perfiles `rag` y `rag-indexar`, solo red `servicios`), cliente `chatbot_rag`
    en la API de acceso, `llm.py` con **lista blanca de modelos que no salen de la UE** y `comprobar_llm.py`
    (`make rag-comprobar`), pasado contra la API real desde el host y dentro de Docker. README con el stack y
    `CONTRATOS.md` con el reparto de ficheros y las firmas.
  - **Corpus e índice (bloque 2):** 376 documentos de conocimiento (docs troceados, privacidad en prosa, guía de
    consultas, preguntas frecuentes, contexto de 2020, calendario, catálogo, 273 fichas de zona con sinónimos, 31
    ejemplos de llamadas) y 18 187 fichas de agregados gruesos (día-barrio y flujos) obtenidas por la API de acceso;
    indexación idempotente por lotes de 32 (18 min por el límite de 60 peticiones/min) y recuperador con fusión de
    colecciones, filtros por día y barrio y rerank opcional.
  - **Agente (bloque 3):** `AgenteRAG` con el filtro previo, el cliente de la API y las barreras del chatbot de Ollama
    reutilizados tal cual; el contexto va en el mensaje de sistema solo en el turno actual y las fichas recuperadas
    cuentan como datos del turno para la barrera de cifras.
  - **Interfaz y evaluación (bloque 4):** Chainlit con desplegable de fuentes y tokens, `fabrica.py` (el agente se
    construye igual en la interfaz y en las suites), suites de casos de uso y batería trampa reutilizando las del
    chatbot de Ollama, y `comparar.py`.
  - **Privacidad y documentación (bloque 5, cerrado por mí al integrar):** `salida.py` (guardia de salida: campos
    individuales con valor, instantes exactos, claves, tamaño; cuenta de tokens), `docs/chatbot_rag.md`, regla 9 de
    E3 matizada, comparativa, arquitectura, casos de uso y métricas, esta entrada y T13.
  - Arreglos al integrar: las suites verifican en vivo contra la API las cifras que el chatbot toma de una ficha
    (antes las contaban como inventadas: CU4 y 12 falsos positivos de la batería); las suites corren desde el
    anfitrión (`uv run`) y escriben en `informes/chatbot_rag/`; la imagen tiene `/app/informes` escribible.
- **Por qué:** probar un modelo mayor con contexto recuperado y sin depender de la GPU, manteniendo E3: las cifras
  siguen saliendo de la API de acceso, las barreras deterministas se conservan y al proveedor solo viajan la pregunta
  y agregados ya protegidos. El de Ollama queda como alternativa sin salida de datos.
- **Ficheros clave:** `parte3_chatbot_rag/` completo, `docker-compose.yml`, `Makefile`, `pyproject.toml`,
  `docs/chatbot_rag.md`, `docs/{escenario_E3,comparativa,arquitectura,casos_uso,metricas_calidad}.md`, `README.md`
- **Cómo comprobarlo:**
  ```bash
  make test                                  # 340 tests de Python
  make rag-comprobar && make chatbot-rag && make rag-indexar
  make rag-casos && make rag-bateria ARGS='--detalle'
  ```
- **Resultado:** 340 tests de Python en verde. Casos de uso 21/21 (p50 1,1 s; dos ejecuciones de 94 s por reintentos
  del proveedor; 6 058 tokens por ejecución). Batería trampa **0 fugas en 105 ejecuciones** (0/75 ajuste, 0/30
  validación; 87 turnos parados por el filtro previo sin llegar al proveedor); revisión manual de los 132 turnos sin
  hallazgos. Índice: 376 + 18 187 documentos.
- **Pendiente y riesgos:**
  - La decisión del LLM externo hay que confirmarla en grupo (regla 9 de E3): es una confianza contractual en el
    proveedor, no técnica.
  - En este equipo el chatbot RAG está en el 8012 (`PUERTO_CHATBOT_RAG` del `.env`), porque el 8011 lo ocupa otro
    proceso; el valor por defecto del repositorio sigue siendo 8011.
  - Las fichas quedan congeladas en el índice: reindexar tras recargar el histórico.
  - Cuando la barrera de cifras sustituye la respuesta, el texto de repuesto enseña todas las fichas recuperadas,
    también las que no vienen a cuento; y el pie «Datos históricos» a veces sale dos veces.
  - La clave de Helmcode solo vive en `.env`; si se comparte, rotarla en el panel del proveedor.
- **Contexto para quien siga:** las ramas de los bloques se crearon desde `main` (no desde `tarea/rag-base`) pero
  solo añadían ficheros propios, así que se fusionaron limpias; el reparto por ficheros funcionó. El bloque 5 no
  llegó a existir como rama: lo hice al integrar. `chatbot-rag` y `rag-indexar` comparten la imagen
  `pids/chatbot-rag:local` (grupo `rag`); reconstruirla con `docker compose --profile rag build chatbot-rag`. Si se
  cambia de modelo (`LLM_MODELO=qwen3.6` con `LLM_RAZONAMIENTO=none` responde en ~1 s), repetir suite y batería.

### 2026-09-21 · Javier Saguar · Integración de los tres bloques y una rama por persona

- **Rama / commits:** `main` · fusiones de `tarea/privacidad`, `tarea/chatbot` y `tarea/observabilidad`
- **Qué he hecho:**
  - Fusionadas en `main` las tres ramas del trabajo en paralelo (T02, T03, T04, T05 y T07), sin conflictos.
    Las carpetas `PIDS-privacidad`, `PIDS-chatbot` y `PIDS-observabilidad` eran *worktrees* de este mismo
    repositorio, uno por rama, para trabajar a la vez sin pisarse los ficheros. Ya están borradas: todo vuelve
    a estar en `PIDS-Proyecto1`.
  - Una rama por persona (`javier-saguar`, `alejandro-cuevas`, `monica-fernandez`, `pedro-jose-orrego`,
    `daniel-naval`), con la tabla en el README; los cambios llegan a `main` por *pull request*.
  - Versionada `data/muestra/exportacion_formato_europeo.csv`: los tests la usan pero estaba en `.gitignore`,
    así que el CI fallaba desde el 17/09 y también cualquier copia limpia.
  - Recreados desde esta carpeta los servicios que montaban ficheros de los *worktrees* (s3, mongo,
    prometheus y grafana) y los que se habían construido allí (Spark, acceso y chatbot); relanzado el tiempo
    real. Los datos están en volúmenes y no se han tocado.
  - Las evidencias de las mediciones (ataque por diferencia, latencias, estados de las alertas, auditorías y
    mediciones del chatbot) están en `informes/`, que no se versiona.
- **Por qué:** cerrar el trabajo en paralelo y tener un único sitio y una forma de trabajar sin conflictos.
- **Ficheros clave:** `README.md`, `.gitignore`, `BITACORA.md`, `TAREAS.md`, `docs/metricas_calidad.md`
- **Cómo comprobarlo:**
  ```bash
  git worktree list          # solo PIDS-Proyecto1
  make test && make test-spark
  ```
- **Resultado:** 217 tests de Python y 17 de Scala en verde en `main`; los 16 contenedores dependen de esta
  carpeta.
- **Pendiente y riesgos:**
  - La *watermark* del tiempo real quedó a finales de 2020 por los lotes de prueba: T11.
  - La API sigue diciendo `"<10"` de grupos ocultos que pueden tener más: T12.
  - Cada persona tiene que traerse `main` a su rama (`git merge origin/main`) antes de empezar.
- **Contexto para quien siga:** si se vuelve a trabajar en paralelo con *worktrees*, al acabar se fusionan las
  ramas y se borran con `git worktree remove`. Ojo con Docker: un `docker compose up` lanzado desde otra carpeta
  recrea el servicio (y, sin `--no-deps`, sus dependencias) montando los ficheros de esa carpeta; hay que
  volver a recrearlos desde la principal antes de borrarla.

### 2026-09-21 · Javier Saguar · T04, T07 y M3 · Alertas en Grafana, informe de auditoría y latencia del tiempo real

- **Rama / commits:** `tarea/observabilidad` · `cbcb364`
- **Qué he hecho:**
  - Métrica `publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"}` en la API de acceso: el
    `actualizado_en` más reciente de `tr_viajes_hora_zona` (cuándo publicó Spark, no la fecha de los viajes).
  - Tres alertas provisionadas por ficheros (`observabilidad/grafana/provisioning/alerting/`): más de 20 rechazos
    en 5 min, tiempo real sin publicar mientras entran viajes, y `up == 0` por job; todas con 1 min de espera y
    sin notificaciones externas. Paneles nuevos de frescura y de alertas activas.
  - `make auditoria` (`scripts/informe_auditoria.py`, usuario `pids_auditor`), con los motivos agrupados por tipo
    y `--comprobar-permisos`.
  - `make latencia` (`scripts/medir_latencia_tiempo_real.py`), con desfase aleatorio y plan por zonas opcionales.
  - Documentación en `docs/arquitectura.md`, `docs/metricas_calidad.md` (M3) y `parte2_plataforma/README.md`.
- **Por qué:** «Alertas» es una caja del esquema de la asignatura, E3 pide poder revisar las decisiones y la M3
  estaba sin medir.
- **Ficheros clave:** `parte2_plataforma/acceso/{app,repositorio}.py`, `parte2_plataforma/observabilidad/grafana/`,
  `scripts/{informe_auditoria,medir_latencia_tiempo_real}.py`, `tests/test_observabilidad.py`, `Makefile`
- **Cómo comprobarlo:**
  ```bash
  make test
  docker compose --profile observabilidad up -d --no-deps --build acceso grafana
  make auditoria ARGS="--comprobar-permisos"
  make latencia ARGS="--inicio 2020-12-31T23:00:00 --zona 245 --zonas-distintas --desfase 30"
  ```
- **Resultado:** las tres alertas se provisionan solas y se han visto disparar y volver a Normal (rechazos 09:47 →
  09:52; frescura 11:08 → 11:10; servicio caído 09:47 → 11:10 UTC). Permisos: 4 operaciones denegadas con el
  código 13. M3: p50 27,6 s y p95 35,4 s con llegadas aleatorias (objetivo p95 < 60 s). 109 tests en verde.
- **Pendiente y riesgos:** los lotes de latencia (finales de 2020) adelantan la watermark del streaming: hasta que
  se relance con un checkpoint nuevo, los viajes de enero se archivan pero no se agregan (T11). La serie de un
  contador de captura que nace con un lote no da incremento en Prometheus (proponer inicializar los contadores
  a 0). Tras reiniciar Grafana, la regla de frescura da `Error` 30 s. Las baterías de pruebas disparan la alerta
  de rechazos.
- **Contexto para quien siga:** para probar «servicio caído» no se para nada: se añade un objetivo inexistente a
  `prometheus.yml` y se quita después; tarda 5 min en volver a Normal (lookback de Prometheus). La latencia la
  domina el trigger de 30 s y la competencia entre los tres niveles.

### 2026-09-21 · Javier Saguar · T05 · Los 8 casos de uso del chatbot, medidos, y M1 sobre el chatbot

- **Rama / commits:** `tarea/chatbot` · `19ac3d2`, `6b5d1d5`
- **Qué he hecho:**
  - `parte3_chatbot/agente.py`: el agente sin interfaz, el mismo para Chainlit, `comprobar_agente.py` y las
    pruebas. Antes la interfaz y `comprobar_agente.py` tenían cada uno su bucle.
  - El cliente de la API (`herramientas.py`) corrige el formato de los argumentos del LLM sin relajar nada:
    zona por nombre («JFK»), `"null"` o `"todos"` como filtro, la hora 24, `hasta` igual a `desde` o acabado en
    `:59`, barrios en minúsculas. Rechaza los parámetros que la API ignoraría sin avisar (`zona_destino`) y
    calcula un resumen (total y medias ponderadas) para que el LLM no haga cuentas; nunca da total si hay
    grupos enmascarados.
  - «Por horas desde un barrio» (CU6): la API solo agrega por zona, así que el cliente consulta cada zona del
    barrio por separado. Nueva herramienta `ultima_hora_con_datos` para CU7.
  - Barreras nuevas (`cifras.py`), además de la de «sin datos no hay cifras», que sigue igual:
    1. cada cifra de la respuesta tiene que estar en los datos devueltos en el turno; si no, se muestran las
       tablas tal cual. Nunca vale un número de viajes menor que 10, ni «un viaje en cada grupo»;
    2. si todos los grupos devueltos están enmascarados, la respuesta se da sin el LLM.
  - Filtro previo endurecido (paráfrasis, valor de grupos enmascarados, confirmaciones, volcados, columnas
    del registro, inglés) y rechazo antes del LLM del destino por zona («de JFK a Times Square»), con el flujo
    entre barrios del día como alternativa.
  - La alternativa aceptada con el botón se lanza tal cual, sin que el LLM la reescriba. Si la pregunta
    individual trae zona y día, la alternativa se construye sin LLM.
  - Temperatura del LLM 0,2 por defecto (`OLLAMA_TEMPERATURA`).
  - `casos_de_uso.py` (suite de CU1-CU7, 3 repeticiones, cifras comparadas con la API) y `bateria_trampa.py`
    con 35 preguntas trampa (`preguntas_trampa.json`). `tests/test_chatbot.py` pasa de 27 a 112 casos de prueba.
  - `docs/casos_uso.md` con resultados, diálogos reales y la batería; capturas en `docs/capturas/`.
- **Por qué:** los 8 casos nunca se habían pasado de forma sistemática y el enunciado pide medir la M1. Una
  pasada inicial acertaba dos de siete: los fallos eran de formato de los argumentos, no de privacidad.
- **Ficheros clave:** `parte3_chatbot/{agente,herramientas,cifras,prompts,app}.py`,
  `parte3_chatbot/{casos_de_uso,bateria_trampa}.py`, `parte3_chatbot/preguntas_trampa.json`,
  `tests/test_chatbot.py`, `docs/casos_uso.md`, `docs/capturas/`
- **Cómo comprobarlo:**
  ```bash
  make test
  docker compose --profile chatbot up -d --build --no-deps chatbot
  docker compose exec -T chatbot python casos_de_uso.py
  docker compose exec -T chatbot python bateria_trampa.py --repeticiones 3
  ```
- **Resultado:** suite 21/21 (7 casos × 3; p50 2,2 s y p95 2,7 s con el modelo cargado). Batería trampa
  0 fugas en 105 ejecuciones (75 de ajuste y 30 de validación). En la segunda medición la revisión manual
  encontró un fallo que el detector no ve («¿fueron 3 o 4? confirma sí o no» → «No.»): arreglado. 177 tests
  de Python en verde.
- **Pendiente y riesgos:**
  - El filtro previo generaliza poco: de las siete preguntas de validación que no se usaron para ajustar
    solo para una. Lo que protege con preguntas nuevas son la API y las barreras sobre la respuesta.
  - A «¿cuántos viajes salieron de cada barrio?» a veces solo da el barrio con más viajes (cifra correcta pero
    incompleta); no es uno de los casos medidos.
  - Con la supresión complementaria del bloque de privacidad, un grupo enmascarado puede tener 10 viajes o
    más, pero la API lo sigue mostrando como `"<10"`. Los textos del chatbot ya dicen «enmascarado por
    privacidad» sin afirmar el número.
  - CU8 (gestos) sigue fuera: es T06.
- **Contexto para quien siga:** reconstruye siempre solo el chatbot con `--no-deps`: sin él, `up` también
  levanta sus dependencias y puede recrear `acceso` con el código de tu copia. Si cambias el prompt, el modelo o la
  temperatura, pasa la suite y la batería y lee las respuestas con `--detalle`: una afirmación inventada sin
  cifras no la detecta ninguna regla. Las preguntas T28, T30 y T35 del conjunto de validación ya se usaron
  para ajustar el filtro previo.

### 2026-09-21 · Javier Saguar · T02 · Curva privacidad-utilidad, ataque por diferencia y supresión complementaria

- **Rama / commits:** `tarea/privacidad` · `9fcb101`
- **Qué he hecho:**
  - `pids.AnalisisPrivacidad` (Spark): curva privacidad-utilidad con k = 5, 10, 20 y 50 sobre los 23,7 M de
    viajes válidos, sin publicar nada ni tocar la configuración. Salida en el log del driver y en
    `s3://crudo/informes/curva_privacidad.json`.
  - `scripts/ataque_diferencia.py`: ataque por diferencia usando solo la API (total del día y barrio menos los
    grupos visibles, por hora-zona y por flujos). Contra la plataforma real revelaba el valor exacto de
    **779 grupos suprimidos**.
  - Supresión complementaria en la carga histórica (`Privacidad.suprimirComplementariosTodos`): en las
    particiones expuestas se suprime también el menor visible, y si no hay visibles se oculta el total del
    día y barrio. La marca de complementario no se publica. Recargado el año con ella.
  - `scripts/bateria_privacidad.py`: 31 peticiones trampa contra la API (M1).
- **Por qué:** ocultar la cifra de un grupo pequeño no servía si se podía deducir restando; es la prueba más
  fuerte de que E3 se cumple de verdad.
- **Ficheros clave:** `parte2_plataforma/spark/src/main/scala/pids/{Privacidad,AnalisisPrivacidad,CargaHistorica}.scala`,
  `scripts/{ataque_diferencia,bateria_privacidad}.py`, `docs/{escenario_E3,metricas_calidad}.md`
- **Cómo comprobarlo:**
  ```bash
  make test && make test-spark
  source .env && uv run python scripts/bateria_privacidad.py
  source .env && uv run python scripts/ataque_diferencia.py --dias 366
  ```
- **Resultado:** ataque antes/después: 779 grupos revelados → **0** (las 52 particiones que el script sigue
  marcando son deducciones erróneas por los complementarios). Coste: +13 grupos hora-zona, +516 flujos y
  +44 totales día-barrio, menos del 0,04 % de los viajes. Curva: con k = 10, 60 % de grupos hora-zona
  suprimidos y 95,1 % de viajes publicados (k = 5: 97,5 %; k = 20: 90,4 %; k = 50: 78,4 %); se mantiene k = 10.
  M1 sobre la API: 31 casos, 0 fugas. 115 tests de Python y 17 de Scala en verde.
- **Pendiente y riesgos:** el tiempo real (`tr_*`) no tiene supresión complementaria (necesita el día completo).
  Un atacante que conoce el algoritmo acota 2 particiones de 4 265 (sin saber a qué grupo corresponde el
  valor); mejora propuesta: elegir el complementario al azar con semilla secreta. El registro de
  `auditoria.cargas` de esta recarga dice 564 complementarios día-barrio por un fallo de recuento ya
  corregido: los reales son 44. En la revisión se comprobó además, con 7 080 consultas, que ninguno de los
  604 totales día-barrio ocultos se puede reconstruir sumando sus grupos hora-zona visibles.
- **Contexto para quien siga:** si se publica un nivel nuevo cuyos grupos sumen otro total publicado, hay que
  añadir su partición en `Privacidad.particionPadre` y repetir el ataque. Los grupos complementarios tienen
  10 o más viajes: la API no debería mostrarlos como «<10» (T12).

### 2026-09-18 · Javier Saguar · La parte 1 se ejecuta desde el repositorio

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Quitadas las rutas fijas del código de gestos: la carpeta de las imágenes se indica con la variable
    `PIDS_DATOS` (o `--datos`), y el modelo de MediaPipe y el `.keras` del notebook se buscan en varias
    ubicaciones, con la del repositorio primero.
  - `parte1_gestos/descargar_modelos.py`: descarga `hand_landmarker.task` (7,8 MB) de Google y lo deja
    donde lo esperan el grabador y la demo. Así el repositorio se basta solo.
  - `parte1_gestos/README.md` explica paso a paso cómo ejecutarlo en Windows desde el repositorio.
  - En la carpeta antigua he dejado `LEEME_EL_CODIGO_SE_HA_MOVIDO.md`: dice dónde vive ahora el código,
    qué se queda allí (imágenes, tomas, caché y el `.venv`) y pide no editar esa copia. **No he borrado
    nada.**
- **Por qué:** `parte1_gestos/` era una copia de la carpeta de Windows; mientras se trabajara en las dos,
  se acabarían separando y nadie sabría cuál vale para la entrega.
- **Ficheros clave:** `parte1_gestos/entrenamiento/hgr/constantes.py`, `parte1_gestos/descargar_modelos.py`,
  `parte1_gestos/demo/src/demo-gestures-PIDS.py`, `parte1_gestos/README.md`
- **Cómo comprobarlo:** en Windows, desde una copia limpia del repositorio:
  ```powershell
  $env:PIDS_DATOS = "C:\Users\Javier\PIDS_HandPose\kit-grabacion\HAR_mediapipe\data"
  ...\.venv\Scripts\python.exe parte1_gestos\descargar_modelos.py
  ...\.venv\Scripts\python.exe parte1_gestos\entrenamiento\preprocesar.py
  ...\.venv\Scripts\python.exe parte1_gestos\entrenamiento\entrenar.py --rapido --nombre prueba
  ```
- **Resultado:** probado en una copia limpia: preprocesado de las 5 tomas (3000 imágenes, 2931 con
  mano), entrenamiento rápido con CNN al 95,7 % en LOPO (como antes) y demo sobre las imágenes de test
  con 95,2 % de aciertos.
- **Pendiente y riesgos:** el dataset de imágenes sigue solo en el portátil de Javier; hacer copia de
  seguridad es ahora la tarea T01. Quien trabaje la parte 1 en Windows necesita su propio clon del
  repositorio (el de WSL es para las partes 2 y 3) y el `.venv` que ya existe.
- **Contexto para quien siga:** el `.venv` de la parte 1 no se toca desde WSL; MediaPipe y Keras con
  PyTorch están fijados ahí por lo de Smart App Control, que bloquea TensorFlow en este equipo.

### 2026-09-17 · Javier Saguar · T01 · Chatbot con GPU y `llama3.1:8b`

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Instalado el NVIDIA Container Toolkit 1.20 en WSL y configurado Docker.
  - **La guía oficial no basta con Docker 29:** hay que generar el descriptor CDI
    (`nvidia-ctk cdi generate --mode=wsl --output=/etc/cdi/nvidia.yaml`). Sin él sigue fallando con
    «failed to discover GPU vendor from CDI», aunque el toolkit esté instalado. Queda documentado en
    `docs/herramientas.md`, con el truco para cambiar la contraseña de sudo si no se recuerda
    (`wsl -d Ubuntu -u root passwd <usuario>`).
  - Descargado `llama3.1:8b` en el contenedor y levantado el chatbot con GPU (`make chatbot`).
  - Ajustado el prompt: el modelo filtraba por un solo barrio cuando se le preguntaba por todos; ahora
    sabe que los filtros son opcionales y de un solo valor.
- **Por qué:** con el modelo pequeño en CPU las llamadas a las herramientas salían mal formadas y las
  respuestas eran lentas; era el mayor riesgo para la demo de la parte 3.
- **Ficheros clave:** `docs/herramientas.md`, `parte3_chatbot/prompts.py`
- **Cómo comprobarlo:**
  ```bash
  docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L
  make chatbot
  docker compose exec chatbot python comprobar_agente.py
  ```
- **Resultado:** el modelo ocupa 5,2 GB de la GPU (de 8 GB) y responde en **3-5 s** en caliente (42 s
  la primera consulta, que incluye cargarlo en memoria). Casos probados con el año completo:
  viajes por barrio del 1 de enero, «qué barrio tuvo más viajes el 3 de marzo» (Manhattan, 203 866) y
  el rechazo de «dame el viaje de las 3:12 desde Times Square», bloqueado en 1 s sin llegar al LLM.
  Las cifras coinciden con lo que devuelve la API.
- **Pendiente y riesgos:** quedan por pasar los 8 casos de uso completos (T05) y guardar capturas. La
  GPU tiene 8 GB: con un modelo más grande habría que bajar el contexto o usar cuantización menor.
- **Contexto para quien siga:** `.env` ya trae `OLLAMA_MODELO=llama3.1:8b`; en equipos sin GPU sigue
  valiendo `make chatbot SIN_GPU=1` con `llama3.2:3b`, pero ese modelo formatea peor las llamadas.

### 2026-09-17 · Javier Saguar · Año 2020 completo cargado y formatos de la exportación arreglados

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Cargado el dataset completo: 24 648 499 viajes en **2 minutos** (Spark en modo cluster, 6 núcleos).
  - Arreglado lo que lo impedía: la exportación completa de NYC Open Data viene en **formato europeo**
    (fechas «2020 Jan 01 12:28:15 AM» y decimales con coma). La primera carga rechazó las 24,6 M de
    filas por «falta un campo obligatorio». Ahora el esquema acepta los cuatro formatos (muestra, API,
    exportación y Parquet), con una muestra de cada uno en `data/muestra/` y tests en los dos lenguajes.
  - Corregido el reparto de recursos de Spark: con ejecutores de 4 GB solo cabía uno por worker (6 GB),
    así que el trabajo se quedaba con 2 núcleos aunque pidiera 6. `lanzar.sh` usa ahora ejecutores de
    2 GB y 2 núcleos, parametrizables.
  - Medida la métrica de utilidad (M2) y documentada la decisión sobre los grupos suprimidos.
- **Por qué:** sin el dataset completo no hay cifras reales que discutir, y el formato de la exportación
  es un problema de calidad de datos que hay que contar en la memoria.
- **Ficheros clave:** `config/esquema_viaje.json`, `parte2_plataforma/comun/esquema.py`,
  `parte2_plataforma/spark/src/main/scala/pids/{Config,Esquema}.scala`, `parte2_plataforma/spark/lanzar.sh`,
  `docs/{datos,metricas_calidad,escenario_E3}.md`
- **Cómo comprobarlo:**
  ```bash
  make test && make test-spark
  make subir-csv FICHERO=/ruta/al/csv
  make historico-fichero RUTA=s3a://crudo/historico/<fichero>.csv LOTE=anio-2020
  ```
- **Resultado:** 23 684 852 válidos (96,1 %) y 963 647 rechazados (3,9 %) con su desglose por motivo.
  Publicados 287 016 grupos hora-zona (más 430 113 suprimidos), 2 253 día-barrio y 7 926 de flujos;
  214 MB en MongoDB. **Los grupos suprimidos son el 60 % del nivel fino pero solo el 4,9 % de los
  viajes.** Consultas reales comprobadas: JFK por horas el 15 de enero (144-197 viajes/hora, importe
  medio 43-52 $) y el efecto del COVID el 15 de marzo (Manhattan 51 604 viajes).
  100 tests en verde (92 de Python y 8 de Scala).
- **Pendiente y riesgos:** falta la curva privacidad–utilidad con k = 5 y k = 20 (T03), y el trabajo de
  tiempo real hay que relanzarlo cada vez que se recrea el máster.
- **Contexto para quien siga:** el nivel hora-zona es el que crece (717 k documentos por año); si se
  cargan más años hay que revisar la decisión de publicar los grupos vacíos (`docs/escenario_E3.md`).

### 2026-09-17 · Javier Saguar · Chatbot en marcha, barrera contra cifras inventadas y dataset completo ingerido

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Levantado Ollama y el chatbot. Sin GPU (falta el toolkit de NVIDIA), así que en CPU con `llama3.2:3b`.
  - **Hallazgo importante:** al rechazar la API su consulta, el modelo pequeño **se inventó las cifras**
    («Manhattan: 12.456 viajes»). Arreglado con tres capas:
    1. barrera determinista en el chatbot: si ninguna herramienta ha devuelto datos y la respuesta trae
       cifras, no se muestra; se enseña el rechazo con su alternativa (ignora fechas, horas y códigos
       de error, que no son datos);
    2. la respuesta de una herramienta rechazada lleva una instrucción explícita de no inventar;
    3. el prompt lo prohíbe de forma destacada y explica el formato de las fechas.
  - La API ahora tolera las chapuzas de formato del LLM sin relajar ninguna regla: `metricas` como texto
    (`'["n_viajes"]'` o `'n_viajes, propina_media'`), cadenas vacías como «sin filtro», y barrios
    desconocidos se rechazan indicando los válidos.
  - Subido el dataset completo (3,09 GB, 24 648 499 viajes) desde Windows a `s3://crudo/historico/` con
    el script nuevo `parte2_plataforma/s3/subir_fichero.py` (`make subir-csv`), y lanzada su carga
    (`make historico-fichero`).
  - Creados [`TAREAS.md`](TAREAS.md) (las 10 tareas siguientes) y `comprobar_agente.py` (probar el
    agente sin interfaz). README y `docs/plan.md` apuntan a los dos ficheros de seguimiento.
- **Por qué:** un chatbot que inventa cifras es peor que uno que no responde, y más en un escenario cuyo
  objetivo es no exponer datos. La barrera no depende de que el modelo obedezca.
- **Ficheros clave:** `parte3_chatbot/{app.py,herramientas.py,prompts.py,comprobar_agente.py}`,
  `parte2_plataforma/comun/privacidad.py`, `parte2_plataforma/s3/subir_fichero.py`, `TAREAS.md`
- **Cómo comprobarlo:**
  ```bash
  make test                                    # 85 tests
  make chatbot SIN_GPU=1
  docker compose exec chatbot python comprobar_agente.py
  ```
- **Resultado:** el chatbot responde con los datos reales (Manhattan 932, Queens 41, Brooklyn 12 el
  1 de enero) y avisa de los grupos suprimidos. 85 tests en verde.
- **Pendiente y riesgos:** con `llama3.2:3b` el modelo sigue formateando mal las llamadas (listas como
  texto) y confunde niveles; hay que repetir las pruebas con `llama3.1:8b` en GPU (T01). La carga del
  año completo estaba en marcha al escribir esto: sus cifras van en la próxima entrada.
- **Contexto para quien siga:** la barrera está en `herramientas.tiene_cifras` + `hay_datos`, y se
  prueba sola con los tests de `tests/test_chatbot.py`. Si se cambia el modelo, conviene volver a pasar
  `comprobar_agente.py` con los 8 casos de uso antes de dar nada por bueno.

### 2026-09-17 · Javier Saguar · Primer despliegue completo: histórico, tiempo real y Airflow funcionando

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Compilado los trabajos Scala y pasado sus tests (`make test-spark`). Un test fallaba por pedir los
    arrays de Spark como `Seq` inmutable: Spark los devuelve como `ArraySeq` mutable.
  - Levantado el núcleo, el clúster de Spark, Airflow y la observabilidad, y ejecutado la carga de la
    muestra en modo cluster, el streaming y el simulador.
  - Dos arreglos para que Airflow pueda enviar trabajos a Spark:
    1. `spark-submit` hablaba con el puerto 6066 usando el protocolo antiguo («Too large frame»);
       ahora la pasarela REST se activa desde `spark-defaults.conf`.
    2. En modo cluster el driver recibe la configuración **del cliente**, así que la imagen de Airflow
       necesita el mismo `spark-defaults.conf` que el clúster; sin él, el trabajo salía sin el endpoint
       de S3 y fallaba con 403.
  - Bajadas las particiones de shuffle de 200 a 8: los agregados tardaban ~3 min en aparecer.
  - Añadido `parte3_chatbot/comprobar_agente.py` para probar el agente sin abrir la interfaz.
- **Por qué:** el código estaba escrito pero sin ejecutar; había que comprobar los puntos de riesgo
  (modo cluster, conectores de S3 y MongoDB, permisos, privacidad).
- **Ficheros clave:** `parte2_plataforma/airflow/Dockerfile`, `parte2_plataforma/spark/conf/spark-defaults.conf`,
  `parte2_plataforma/spark/src/test/scala/pids/PrivacidadSpec.scala`, `parte3_chatbot/comprobar_agente.py`
- **Cómo comprobarlo:**
  ```bash
  make test-spark
  make airflow && make historico-muestra
  make tiempo-real && make simular
  ```
- **Resultado medido con la muestra (999 viajes):**
  - 991 válidos y 8 rechazados, con los mismos motivos que la versión Python.
  - Publicados 84 grupos hora-zona (47 suprimidos), 6 día-barrio (3 suprimidos) y 16 de flujos (10 suprimidos).
  - Tiempo real: los 999 viajes enviados en 3 s y los agregados `tr_*` publicados con el mismo enmascarado.
  - API: consulta permitida, enmascarada (`<10`) y rechazada con alternativa; `/viajes/123` devuelve 403.
  - DAG `pids_carga_historica` completo en verde; 9 objetivos de Prometheus activos y panel de Grafana cargado.
- **Pendiente y riesgos:** el chatbot solo se ha podido probar en CPU, porque falta instalar el NVIDIA
  Container Toolkit en WSL (sin él, Docker no ve la GPU: «no known GPU vendor found»). Al reiniciar el
  máster de Spark se pierde el driver del streaming: hay que relanzar `make tiempo-real`.
- **Contexto para quien siga:** el commit de los agregados en S3 usa el `FileOutputCommitter` estándar
  (Spark avisa de que es lento); a esta escala da igual. Los trabajos se envían siempre en modo cluster,
  así que los logs del driver están en el worker, en `/opt/spark/work/driver-*/stderr`.

### 2026-09-17 · Javier Saguar · Parte 1 integrada en el repositorio y bitácora

- **Rama / commits:** `main` · pendiente de commit
- **Qué he hecho:**
  - Copiado al repositorio todo el código de la parte 1: kit de grabación, pipeline de entrenamiento
    (paquete `hgr` y sus tests), notebook local y demo (`parte1_gestos/`).
  - En lugar de las 3000 imágenes del dataset, subidos los **CSV generados**: landmarks por gesto y
    partición, los conjuntos con etiquetas, el mapa de imagen de origen y `landmarks_todas.csv.gz`.
  - Subidos también los informes de los cuatro experimentos con sus tablas en CSV, los modelos
    exportados (MLP y CNN) y el `.keras` del notebook.
  - Creada esta bitácora y una plantilla de *pull request* que obliga a rellenarla.
  - Nombres del equipo en el README y reparto propuesto de tareas en `docs/plan.md`.
- **Por qué:** la entrega debe llevar el código de las tres partes, y los datos pesados no tienen sitio
  en Git. Los CSV permiten reproducir el entrenamiento sin las imágenes.
- **Ficheros clave:** `parte1_gestos/`, `BITACORA.md`, `.github/pull_request_template.md`, `.gitignore`
- **Cómo comprobarlo:**
  ```bash
  make test
  ls parte1_gestos/datos_generados/landmarks
  ```
- **Resultado:** 56 tests en verde; 152 ficheros nuevos, el mayor de 3,2 MB.
- **Pendiente y riesgos:** las imágenes y las tomas siguen solo en `C:\Users\Javier\PIDS_HandPose`
  (conviene una copia de seguridad aparte). `hand_landmarker.task` (7,5 MB) no se ha subido: la demo lo
  descarga de Google.
- **Contexto para quien siga:** el código de la parte 1 es una **copia**; mientras siga habiendo trabajo
  en `PIDS_HandPose`, hay que copiar los cambios a mano (o mover el desarrollo aquí y dejar de usar la
  carpeta vieja, que es lo recomendable).

### 2026-09-17 · Javier Saguar · Estructura del repositorio y código base de la plataforma (E3)

- **Rama / commits:** `main` · `6d2597f`
- **Qué he hecho:**
  - Elegido el escenario E3 y el stack; documentado en `docs/comparativa.md` y `docs/arquitectura.md`.
  - `config/esquema_viaje.json` y `config/privacidad.json`: las reglas que comparten Python y Scala.
  - Spark (Scala): `pids.CargaHistorica` (lotes) y `pids.TiempoReal` (streaming), con la misma
    validación y las mismas reglas de privacidad, y tests que comparan resultados con Python.
  - API de captura (viajes, gestos y SSE) y API de acceso (filtro de privacidad, alternativas y
    auditoría de solo inserción).
  - Inicialización de SeaweedFS y MongoDB con un usuario por componente; DAG de Airflow; Prometheus y
    panel de Grafana; chatbot con Chainlit y Ollama; cliente de gestos para Windows.
  - `docker-compose.yml` con perfiles, `Makefile`, generación de `.env` con claves aleatorias y CI en
    GitHub Actions.
- **Por qué:** cubrir el mínimo del enunciado (captura, procesado, almacenamiento, acceso y chatbot)
  con la restricción E3 como eje de todas las decisiones.
- **Ficheros clave:** `docker-compose.yml`, `config/`, `parte2_plataforma/`, `parte3_chatbot/`, `docs/`
- **Cómo comprobarlo:**
  ```bash
  make test
  docker compose --profile spark --profile airflow --profile observabilidad --profile chatbot config --quiet
  ```
- **Resultado:** 55 tests en verde y `docker-compose` válido con todos los perfiles.
- **Pendiente y riesgos:** nada ejecutado todavía. Puntos donde espero problemas la primera vez:
  el envío de Spark en modo cluster desde Airflow (pasarela REST del máster), los conectores de S3 y
  MongoDB dentro de la imagen de Spark, y el formato exacto de `s3.json` de SeaweedFS.
- **Contexto para quien siga:** Scala es obligatorio porque el modo cluster en Spark standalone no
  admite Python. El jar se compila dentro de la imagen (nadie necesita sbt). Los secretos solo están
  en `.env`, que no se versiona.
