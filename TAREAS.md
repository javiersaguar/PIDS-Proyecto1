# Próximas tareas

Lista viva de las **10 tareas siguientes**, en orden de prioridad. Si te pones a trabajar, coge la
primera que esté libre. Las tareas del chatbot RAG que quedaron por hacer están en «Ideas y trabajo futuro».
El mapa de todo lo que falta para cerrar el proyecto está en
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

## T10 · Entrega: vídeo y presentación

- **Estado:** libre · **Responsable:** — · **Estimación:** 6 h (entre varios) · **Dificultad:** baja
- **Por qué:** es lo que se entrega y se puntúa (diapositiva 10).
- **Qué hay que hacer:**
  1. Vídeo: levantar la plataforma, cargar datos, ver el panel, conversar con el chatbot (incluido un
     rechazo por privacidad) y, si está, el gesto.
  2. Presentación: reparto del trabajo, comparativa, arquitectura, casos de uso, demo y conclusiones.
  3. Repasar el checklist de `docs/plan.md`.
- **Notas:** el guion está escrito: [`docs/guion_demo.md`](docs/guion_demo.md) (escenas, qué se dice, qué objetivo
  cubre cada una y plan B). El gesto ya no necesita Windows: la escena 9 se hace en el portal con TAXI AI →
  «Gestos» (antes, probarlo: T18). Grabar con el portal ya abierto: la contraseña no sale en el vídeo. No lanzar cargas durante
  la grabación (T19).
- **Hecha cuando:** el vídeo y las diapositivas están listos y enlazados desde el README.
- **Dónde:** `docs/`, README

## T18 · Probar los gestos con la webcam de verdad

- **Estado:** libre · **Responsable:** — · **Estimación:** 30 min · **Dificultad:** baja
- **Por qué:** los gestos del portal están probados con una cámara simulada hecha con fotos del dataset, pero no con
  una webcam real, con su luz y su encuadre; y el 22/09 la del portátil daba fotogramas negros (obturador o tapa).
  Es la escena 9 de la demo.
- **Qué hay que hacer:**
  1. En el portátil, http://localhost:8020 → TAXI AI → «Gestos»: los seis gestos, con la mano a distintas distancias
     y con las dos manos. Apuntar cuáles cuestan.
  2. Lo mismo en https://happytaxi-rust.vercel.app, en vivo y en la demostración (y en un móvil, que también vale).
  3. Si algún gesto no entra, probar a subir o bajar `confianza_minima` en `config/gestos.json` (0,85) antes de
     tocar el modelo.
- **Hecha cuando:** los seis gestos funcionan con la cámara que se va a usar en la demo, en local y en Vercel.
- **Dónde:** `config/gestos.json`, `integracion/README.md`

## T19 · Que la muestra no pise el histórico

- **Estado:** libre · **Responsable:** — · **Estimación:** 1 h · **Dificultad:** media
- **Por qué:** los agregados se guardan por sus dimensiones, así que la carga de la muestra (999 viajes del 1 de
  enero) sustituye los grupos del 1 de enero cargados con el año completo. Pasó el 22/09 con tres cargas desde
  Operaciones y se reparó repitiendo la carga del año.
- **Qué hay que hacer:** que `POST /api/operaciones/airflow/cargas` y el DAG respondan 409 a `muestra` si
  `auditoria.cargas` ya tiene una carga que no sea de la muestra, con un mensaje que lo explique; en Operaciones,
  la casilla de la muestra deshabilitada con ese motivo. Tests del BFF y del DAG.
- **Hecha cuando:** con el año cargado, la muestra no se puede lanzar ni desde el portal ni desde Airflow.
- **Dónde:** `parte4_frontend/bff/rutas/operaciones.py`, `parte2_plataforma/airflow/`, `web/src/paginas/operaciones/`

---

## Ideas y trabajo futuro

- Chatbot RAG: cuando la barrera de cifras sustituye la respuesta, enseñar solo las fichas relacionadas con la
  pregunta (hoy salen todas las recuperadas); quitar el pie «Datos históricos» duplicado cuando el modelo ya lo
  escribe; medir el rerank (`RAG_RERANK=true`) con la suite; reindexar las fichas desde Airflow tras cada carga.
- Chatbot RAG: probar `qwen3.6` con `LLM_RAZONAMIENTO=none` (responde en ~1 s) con la suite y la batería completas.
- Portal web: usuarios y roles (hoy una contraseña única), exportar a CSV la tabla del explorador, persistir en la URL el
  selector de horas del tiempo real, y modo oscuro con las variables del tema.
- Portal web, actividad en vivo (T15): pedir al BFF las *task instances* del DAG para iluminar solo la tarea en curso
  de una carga (hoy se enciende el camino entero, porque Airflow solo da el estado de la ejecución); y empujar la
  actividad por SSE desde el BFF en vez de sondear cada 2-15 s.
- Privacidad diferencial (OpenDP) sobre los agregados, además del umbral k.
- Detectar patrones de consultas sospechosos por cliente (muchas consultas solapadas).
- Airflow: un DAG que cargue los 12 meses en cadena, con reintentos.
- Gestos: un tramo propio en el grafo (Redpanda → Chatbots) en vez de la pastilla; un gesto para «pulgar abajo»
  (reentrenar con una clase más); los gestos también en el explorador (siguiente ejemplo, consultar).
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
| 22/09/2026 | T06 Integración de los gestos: 👍 ejecuta la alternativa y ✋ la cancela, con vídeo | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T09 API de acceso con dos réplicas detrás de Caddy: 2555 peticiones con una réplica parada y otra tirada, 0 fallos | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T16 Botón «TAXI AI» con el chatbot en un panel derecho, disponible en todas las páginas | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T15 Animaciones en vivo del portal: el grafo ilumina los tramos en marcha, indicador «En vivo» y gráficas que se mueven con los datos nuevos | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T11 Tiempo real desde cero (`make tiempo-real-reiniciar`) y captura en directo con viajes reales de diciembre de 2020 (`make capturar`, botón del grafo) | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T12 La API etiqueta todos los grupos suprimidos como `oculto` (un complementario puede tener 10 o más viajes) | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T13 El LLM externo de Helmcode se queda (Vigente): la demo enseña los dos chatbots | Javier Saguar | entrada del 22/09 |
| 22/09/2026 | T17 Gestos de la parte 1 en los tres chatbots (Chainlit de Ollama y RAG, y TAXI AI) y reconocidos en el navegador con el MLP de la parte 1, también en Vercel | Javier Saguar | entrada del 22/09 |
