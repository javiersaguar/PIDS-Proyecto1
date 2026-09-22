# Próximas tareas

Lista viva de las **10 tareas siguientes**, en orden de prioridad. Si te pones a trabajar, coge la
primera que esté libre. Las tareas del chatbot RAG que quedaron por hacer están en «Ideas y trabajo futuro» y la
decisión pendiente en T13. El mapa de todo lo que falta para cerrar el proyecto está en
[`docs/pendiente.md`](docs/pendiente.md).

## Cómo se usa

1. **Coge una tarea:** pon tu nombre en «Responsable» y el estado en `en curso`.
2. **Al terminar:** marca `hecha ✅`, muévela al final, a «Tareas terminadas», con la fecha, y escribe
   la entrada correspondiente en [`BITACORA.md`](BITACORA.md) (esta lista dice *qué* hacer; la bitácora
   cuenta *qué se hizo*).
3. **Si añades trabajo nuevo:** apúntalo abajo, en «Ideas y trabajo futuro», y súbelo a la lista de 10
   solo cuando quede hueco. La lista no debe crecer: si todo es urgente, nada lo es.
4. **Si la dejas a medias:** deja el estado en `en curso`, escribe en «Notas» qué falta exactamente y
   cuéntalo en la bitácora.
5. **Si trabajas con una IA:** dale primero `BITACORA.md` y este fichero; así sabe el estado real y la
   tarea concreta, sin reinventar lo ya hecho.

| Estado | Significado |
|---|---|
| `libre` | Nadie la ha cogido |
| `en curso` | Alguien está con ella (mira «Notas») |
| `bloqueada` | Depende de otra tarea o de algo externo |
| `hecha ✅` | Terminada y con entrada en la bitácora |

---

## T01 · Copia de seguridad del dataset de gestos

- **Estado:** en curso · **Responsable:** Javier Saguar · **Estimación:** 30 min · **Dificultad:** baja
- **Por qué:** las 3000 imágenes y las 5 tomas originales **solo existen en el portátil de Javier**
  (`C:\Users\Javier\PIDS_HandPose`), porque no caben en el repositorio. Si se pierde ese disco, se pierde
  el dataset del proyecto y no se puede volver a grabar (cinco personas, una tarde).
- **Qué hay que hacer:**
  1. Comprimir `kit-grabacion\HAR_mediapipe\data` (las 5 tomas con su metadata.json).
  2. Subirlo a un sitio compartido del grupo (Drive de la universidad, por ejemplo) y anotar el enlace
     en `parte1_gestos/README.md`.
  3. Comprobar que alguien más del grupo puede descargarlo y ejecutar `preprocesar.py` con él.
- **Hecha cuando:** otro miembro del grupo ha reproducido el preprocesado desde la copia.
- **Dónde:** `parte1_gestos/README.md`
- **Notas (21/09):** paso 1 hecho: `dataset_gestos_PIDS_2026-09-16.zip` (598,9 MiB; SHA-256 y contenido en
  `parte1_gestos/README.md`), verificado en el portátil con `preprocesar.py` desde una copia limpia (3000
  imágenes, 2931 con mano). Falta subirlo a un sitio compartido **solo con el grupo**, anotar el enlace en el
  README y que otra persona lo descargue y reproduzca el preprocesado.

## T06 · Integración de los gestos (última fase del esquema)

- **Estado:** en curso · **Responsable:** Javier Saguar · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** es la caja «Integración» de la diapositiva 5 (opcional, pero puntúa). El chatbot ya ofrece
  la alternativa con botón tras un rechazo y la lanza tal cual al aceptarla; el gesto 👍 hace lo mismo.
- **Qué hay que hacer:**
  1. Llamar a `EmisorGestos.observar(pred, conf)` desde `parte1_gestos/demo/src/demo-gestures-PIDS.py`.
  2. `GESTOS_ACTIVOS=true` en `.env` y reiniciar el chatbot.
  3. Probar el ciclo completo: el bot propone una alternativa → 👍 la ejecuta, ✋ la cancela.
- **Hecha cuando:** se graba un vídeo corto en el que un gesto confirma una consulta del chatbot.
- **Dónde:** `integracion/`, `parte1_gestos/demo/src/`
- **Notas (22/09):** la demo ya llama a `observar`, `GESTOS_ACTIVOS=true` y el ciclo está probado sin cámara
  (el mismo POST que enviaría la demo): 👍 ejecuta la alternativa y ✋ la cancela. Falta el vídeo con la webcam
  en Windows (`PIDS_CLAVE_GESTOS` en la consola de la demo; ver `integracion/README.md`).

## T10 · Entrega: vídeo y presentación

- **Estado:** libre · **Responsable:** — · **Estimación:** 6 h (entre varios) · **Dificultad:** baja
- **Por qué:** es lo que se entrega y se puntúa (diapositiva 10).
- **Qué hay que hacer:**
  1. Vídeo: levantar la plataforma, cargar datos, ver el panel, conversar con el chatbot (incluido un
     rechazo por privacidad) y, si está, el gesto.
  2. Presentación: reparto del trabajo, comparativa, arquitectura, casos de uso, demo y conclusiones.
  3. Repasar el checklist de `docs/plan.md`.
- **Hecha cuando:** el vídeo y las diapositivas están listos y enlazados desde el README.
- **Dónde:** `docs/`, README

## T11 · Tiempo real listo para la demo

- **Estado:** libre · **Responsable:** — · **Estimación:** 1 h · **Dificultad:** media
- **Por qué:** las pruebas de alertas y de latencia del 21/09 enviaron viajes de finales de diciembre de 2020
  y el trabajo de tiempo real tiene ahí su *watermark*: `make simular` con la muestra del 1 de enero archiva
  los viajes pero no los agrega, así que en el vídeo el tiempo real no se movería.
- **Qué hay que hacer:**
  1. Cuando esos lotes hayan salido del topic `viajes-crudos` (retención de 24 h), parar el trabajo de tiempo
     real, borrar su checkpoint (`/opt/spark/checkpoints/tiempo_real`, volumen `spark-checkpoints`) y
     relanzarlo con `make tiempo-real`. Si se quiere empezar sin los lotes de prueba, vaciar también las
     colecciones `tr_*` con el usuario administrador de MongoDB.
  2. Sin esperar, la alternativa es simular un fichero de diciembre (`make descargar MES=2020-12` y
     `make simular FICHERO=data/crudo/...`).
  3. Dejar escrito el procedimiento en `parte2_plataforma/README.md`.
- **Hecha cuando:** `make simular` hace crecer `tr_*` y el chatbot responde CU7 con esos datos.
- **Dónde:** `parte2_plataforma/README.md`, volumen `spark-checkpoints`

## T12 · Etiqueta de los grupos ocultos en la API

- **Estado:** libre · **Responsable:** — · **Estimación:** 1 h · **Dificultad:** baja
- **Por qué:** con la supresión complementaria (T02) hay grupos ocultos con 10 o más viajes, pero la API los
  sigue mostrando todos como `"<10"`, que para esos es falso. El chatbot ya dice «enmascarado por privacidad»
  sin dar el número.
- **Qué hay que hacer:** en `parte2_plataforma/comun/privacidad.enmascarar`, devolver `"oculto"` para todos
  los suprimidos (no se puede distinguir cuáles son complementarios: esa marca no se publica); actualizar sus
  tests, `docs/escenario_E3.md` y `docs/casos_uso.md`, y pasar `casos_de_uso.py` y `bateria_trampa.py` del
  chatbot.
- **Hecha cuando:** ninguna respuesta afirma `"<10"` de un grupo que puede tener más.
- **Dónde:** `parte2_plataforma/comun/privacidad.py`, `tests/`, `docs/`

## T13 · Decidir en grupo el LLM externo del chatbot RAG

- **Estado:** libre · **Responsable:** — · **Estimación:** 30 min · **Dificultad:** baja
- **Por qué:** el chatbot RAG (`parte3_chatbot_rag/`) envía la pregunta y los agregados protegidos a Helmcode
  (UE, sin registro de prompts). Matiza la regla 9 de E3 y está anotado en la bitácora como **propuesta**: hay que
  confirmarla o retirarla entre todos, y decidir qué chatbot va en la demo (los dos pasan 21/21 y 0/105).
- **Qué hay que hacer:**
  1. Leer [`docs/chatbot_rag.md`](docs/chatbot_rag.md) («Qué sale del equipo y qué no») y la decisión del 21/09 en la
     bitácora.
  2. Decidir: se mantiene (y pasa a «Vigente»), se limita a la demo, o se retira (basta con no levantar el perfil
     `rag`).
  3. Si se mantiene, cada miembro pega su propia `LLM_API_KEY` en su `.env` (la clave no se comparte por el chat).
- **Hecha cuando:** la decisión figura como «Vigente» o «Retirada» en la bitácora y `docs/plan.md` dice qué chatbot
  se enseña.
- **Dónde:** `BITACORA.md`, `docs/plan.md`

## T15 · Animaciones en vivo del portal

- **Estado:** libre · **Responsable:** — · **Estimación:** 6 h · **Dificultad:** media
- **Por qué:** el panel y el grafo de documentación se quedan quietos aunque estén entrando viajes o
  corriendo una carga. En la demo tiene que verse que la plataforma trabaja.
- **Qué hay que hacer:**
  1. Actualizar las gráficas del panel y de tiempo real cuando cambian los agregados (el sondeo ya existe
     en operaciones; aquí el dibujo tiene que moverse con los datos nuevos).
  2. En el grafo del pipeline (`parte4_frontend/web/src/paginas/documentacion/`), animar los caminos que
     corresponden al proceso en curso: un DAG de carga histórica, o datos nuevos entrando por la captura.
  3. La señal sale de lo que el BFF ya conoce (ejecuciones de Airflow, frescura del tiempo real, simulación
     activa), sin abrir un puerto nuevo.
- **Hecha cuando:** al lanzar un DAG o el simulador, el grafo marca el tramo que está trabajando y las
  gráficas cambian sin recargar la página.
- **Dónde:** `parte4_frontend/web/src/paginas/documentacion/`, `parte4_frontend/web/src/paginas/panel/`,
  `parte4_frontend/web/src/paginas/tiempo-real/`

## T16 · Botón «TAXI AI» con el chatbot en un panel derecho

- **Estado:** libre · **Responsable:** — · **Estimación:** 5 h · **Dificultad:** media
- **Por qué:** el asistente es una sección más del menú izquierdo. Tiene que estar siempre a mano, como
  un acceso del producto, no como otra página.
- **Qué hay que hacer:**
  1. Quitar «Asistente» de la barra izquierda (`navegacion.ts` y la ruta que deja de ser una sección).
  2. Un botón fijo en la esquina inferior derecha con el texto «TAXI AI».
  3. Al pulsarlo, un panel entra desde el borde derecho y ahí está el chatbot (el mismo agente de Ollama o
     RAG que ya usa `/asistente`). Cerrarlo lo esconde; no navega a otra ruta.
- **Hecha cuando:** desde cualquier página del portal se abre y se cierra el chat con ese botón, y el menú
  izquierdo ya no tiene la entrada del asistente.
- **Dónde:** `parte4_frontend/web/src/componentes/shell/`, `parte4_frontend/web/src/paginas/asistente/`

---

## Ideas y trabajo futuro

- Chatbot RAG: cuando la barrera de cifras sustituye la respuesta, enseñar solo las fichas relacionadas con la
  pregunta (hoy salen todas las recuperadas); quitar el pie «Datos históricos» duplicado cuando el modelo ya lo
  escribe; medir el rerank (`RAG_RERANK=true`) con la suite; reindexar las fichas desde Airflow tras cada carga.
- Chatbot RAG: probar `qwen3.6` con `LLM_RAZONAMIENTO=none` (responde en ~1 s) con la suite y la batería completas.
- Portal web: usuarios y roles (hoy una contraseña única), exportar a CSV la tabla del explorador, persistir en la URL el
  selector de horas del tiempo real, y modo oscuro con las variables del tema.
- Privacidad diferencial (OpenDP) sobre los agregados, además del umbral k.
- Detectar patrones de consultas sospechosos por cliente (muchas consultas solapadas).
- Airflow: un DAG que cargue los 12 meses en cadena, con reintentos.
- Comparar la exportación completa con los Parquet mensuales de la TLC (¿mismos viajes?).
- Committer de S3A más rápido para las escrituras de Spark.
- Supresión complementaria también en tiempo real: un trabajo por lotes que cierre cada día cuando la
  *watermark* lo deja atrás y reescriba sus documentos `tr_*`.
- Elegir el grupo complementario al azar con una semilla secreta (hoy es el menor visible, lo que da una cota
  a quien conozca el algoritmo).
- Añadir al ataque por diferencia la reconstrucción de totales ocultos a partir de los grupos hora-zona
  (comprobado a mano el 21/09: 0 de los 604 totales ocultos).
- Bajar la latencia del tiempo real (M3): trigger de 10 s, `PIDS_CORES=4` o los tres niveles en una sola
  consulta.
- API de captura: crear los contadores a 0 al arrancar (una serie que nace con un lote no da incremento en
  Prometheus y la alerta de frescura no lo ve).
- API de acceso: rechazar los campos desconocidos (`extra='forbid'`) y admitir `barrio_origen` en `hora_zona`
  (hoy el chatbot consulta zona a zona).
- Makefile: `make curva-privacidad`, `make ataque-diferencia` y `make bateria-privacidad`.
- Proteger `main` en GitHub para que solo cambie por *pull request*.

## Tareas terminadas

| Fecha | Tarea | Quién | Bitácora |
|---|---|---|---|
| 17/09/2026 | Estructura del repositorio y código base de la plataforma | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Parte 1 integrada (código y CSV generados) y bitácora | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Primer despliegue completo: histórico, tiempo real, Airflow y observabilidad | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Chatbot en marcha (CPU) con barrera contra cifras inventadas | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Dataset completo ingerido y cargado: 23,7 M de viajes válidos en 2 min | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | T01 Chatbot con GPU: toolkit de NVIDIA, `llama3.1:8b` y respuestas en 3-5 s | Javier Saguar | entrada del 17/09 |
| 18/09/2026 | T01 Parte 1 ejecutable desde el repositorio (sin rutas fijas) | Javier Saguar | entrada del 18/09 |
| 21/09/2026 | T02 Curva privacidad-utilidad y ataque por diferencia: 779 grupos revelados → 0 con supresión complementaria | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | T05 Casos de uso del chatbot: 7 casos medidos (21/21), batería trampa (0/105) y capturas | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | T04 Alertas en Grafana: tres reglas provisionadas y probadas | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | T07 Informe de auditoría (`make auditoria`) y prueba de que es de solo añadir | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | T03 Las 3 métricas medidas: M1 0 fugas (API 31, chatbot 105), M2 curva k = 5-50, M3 p95 35,4 s | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | Integración de los tres bloques en `main` y una rama por persona | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | Chatbot RAG con LLM externo (LangChain + Qdrant + Helmcode) en cinco bloques: 21/21 casos, 0/105 fugas, 340 tests | Javier Saguar | entrada del 21/09 |
| 21/09/2026 | T14 Portal web en `main` y levantado desde la carpeta principal (8020), demostración pública en Vercel y capturas | Javier Saguar | entrada del 21/09 |
| 22/09/2026 | T08 Servicios sin login fuera de Docker, login de los chatbots y modelo de amenazas | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T09 API de acceso con dos réplicas detrás de Caddy: 2555 peticiones con una réplica parada y otra tirada, 0 fallos | Javier Saguar | entrada del 22/09 |
