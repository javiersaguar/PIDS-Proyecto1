# Próximas tareas

Lista viva de las **10 tareas siguientes**, en orden de prioridad. Si te pones a trabajar, coge la
primera que esté libre. Las tareas del chatbot RAG que quedaron por hacer están en «Ideas y trabajo futuro» y la
decisión pendiente en T13.

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

- **Estado:** libre · **Responsable:** — · **Estimación:** 30 min · **Dificultad:** baja
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

## T06 · Integración de los gestos (última fase del esquema)

- **Estado:** libre (T05 ya está hecha) · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** es la caja «Integración» de la diapositiva 5 (opcional, pero puntúa). El chatbot ya ofrece
  la alternativa con botón tras un rechazo y la lanza tal cual al aceptarla; el gesto 👍 hace lo mismo.
- **Qué hay que hacer:**
  1. Llamar a `EmisorGestos.observar(pred, conf)` desde `parte1_gestos/demo/src/demo-gestures-PIDS.py`.
  2. `GESTOS_ACTIVOS=true` en `.env` y reiniciar el chatbot.
  3. Probar el ciclo completo: el bot propone una alternativa → 👍 la ejecuta, ✋ la cancela.
- **Hecha cuando:** se graba un vídeo corto en el que un gesto confirma una consulta del chatbot.
- **Dónde:** `integracion/`, `parte1_gestos/demo/src/`

## T08 · Repaso de seguridad y modelo de amenazas

- **Estado:** libre · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** «elementos de autenticación / seguridad» puntúa, y conviene tener escrito qué se protege
  y qué no.
- **Qué hay que hacer:**
  1. Revisar qué puertos se publican y con qué credenciales (la pasarela REST de Spark y la consola de
     Redpanda no tienen autenticación: dejarlas solo en la red interna o detrás de un proxy).
  2. Rotación de claves: comprobar que `make entorno --forzar` y recrear volúmenes funciona.
  3. Escribir `docs/seguridad.md`: qué atacante se considera, qué se protege y qué queda fuera.
- **Hecha cuando:** existe `docs/seguridad.md` y no hay ningún servicio sin autenticación accesible
  fuera de Docker.
- **Dónde:** `docker-compose.yml`, `docs/seguridad.md`

## T09 · Alta disponibilidad de la API de acceso

- **Estado:** libre · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** es uno de los criterios adicionales del enunciado y ahora mismo la API es un único
  contenedor.
- **Qué hay que hacer:** dos réplicas de `acceso` detrás de un proxy (Caddy o Nginx), comprobar que se
  puede tirar una sin cortar el servicio, y documentar qué pasa con el resto de componentes (Spark
  standalone tiene un solo máster: apuntar la limitación).
- **Hecha cuando:** con una réplica parada, el chatbot sigue respondiendo.
- **Dónde:** `docker-compose.yml`, `docs/arquitectura.md`

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

---

## Ideas y trabajo futuro

- Chatbot RAG: cuando la barrera de cifras sustituye la respuesta, enseñar solo las fichas relacionadas con la
  pregunta (hoy salen todas las recuperadas); quitar el pie «Datos históricos» duplicado cuando el modelo ya lo
  escribe; medir el rerank (`RAG_RERANK=true`) con la suite; reindexar las fichas desde Airflow tras cada carga.
- Chatbot RAG: probar `qwen3.6` con `LLM_RAZONAMIENTO=none` (responde en ~1 s) con la suite y la batería completas.
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
