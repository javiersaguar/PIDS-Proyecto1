# Bitácora del proyecto

Registro de cambios escrito por personas, no por Git. Sirve para dos cosas:

1. Que cualquiera del equipo sepa qué ha pasado sin leerse el código ni los commits.
2. Que cualquier asistente de IA que retome el trabajo (Claude, ChatGPT, Gemini, Copilot…) tenga el
   contexto al día y no reinvente ni deshaga lo ya decidido.

## Cómo se usa

- **Antes de trabajar:** lee «Estado actual», «Decisiones tomadas» y las dos o tres últimas entradas,
  y mira qué toca en [`TAREAS.md`](TAREAS.md). Si vas a usar una IA, dale los dos ficheros completos
  como primer contexto.
- **Al terminar, antes del commit o del *pull request*:** añade una entrada nueva **arriba** de la
  lista, actualiza «Estado actual» y marca la tarea en [`TAREAS.md`](TAREAS.md).
- **Si has trabajado con una IA:** la entrada la firma la persona que ha usado y revisado el
  resultado. En el repositorio solo figuramos los cinco del grupo como autores.
- **Si cambias una decisión anterior:** añádela a «Decisiones tomadas» y marca la vieja como
  *sustituida*, explicando por qué. No borres entradas antiguas: esto se escribe añadiendo.
- **Si dejas algo a medias:** dilo en «Pendiente y riesgos». Es la parte más útil para quien siga.
- **Nunca** escribas aquí contraseñas, claves ni rutas con datos personales.

## Estado actual

**Última actualización: 17/09/2026 · Javier Saguar**

| | |
|---|---|
| **Escenario** | E3 · privacidad total |
| **Funciona y está probado en ejecución** | Núcleo (S3, Redpanda, MongoDB, APIs), carga histórica con Spark en modo cluster, tiempo real con streaming y simulador, filtro de privacidad (permitida / enmascarada / rechazada), DAG de Airflow completo, Prometheus (9 objetivos) y panel de Grafana. 92 tests de Python y 8 de Scala |
| **Datos cargados** | Año 2020 completo: 23 684 852 viajes válidos y 287 016 grupos hora-zona publicados |
| **Chatbot** | Con GPU y `llama3.1:8b`: responde en 3-5 s, con la barrera contra cifras inventadas |
| **Sin empezar** | Medición formal de las 3 métricas de calidad, alertas en Grafana, integración de gestos en la demo, vídeo y presentación |
| **Cómo levantarlo** | En Ubuntu (WSL2): `make entorno && make sync && make test && make airflow && make historico-muestra` |
| **Siguientes tareas** | Ver [`TAREAS.md`](TAREAS.md) (T01 a T10) |
| **Pendiente inmediato** | Medir las métricas de calidad M1 y M3 (T03) y pasar los 8 casos de uso del chatbot (T05) |
| **Requisitos** | Todo instalado en este equipo (incluido el NVIDIA Container Toolkit). En equipos sin GPU: `make chatbot SIN_GPU=1` con `OLLAMA_MODELO=llama3.2:3b` |

## Decisiones tomadas

| Fecha | Decisión | Motivo | Quién | Estado |
|---|---|---|---|---|
| 17/09/2026 | Escenario **E3 (privacidad total)** | La demo luce y encaja con la parte 1, que ya procesa en el dispositivo por privacidad | Equipo | Vigente |
| 17/09/2026 | Stack: Docker Compose, Redpanda, Spark 4 en Scala (modo cluster), MongoDB + S3, FastAPI, Airflow, Grafana + Prometheus, Ollama local + Chainlit | Ver `docs/comparativa.md` | Equipo | Vigente |
| 17/09/2026 | **SeaweedFS** como almacenamiento S3 en lugar de MinIO | MinIO retiró sus imágenes de Docker Hub (última publicada en 2025) | Javier Saguar | Vigente |
| 17/09/2026 | Las reglas de validación y privacidad viven en `config/*.json`, compartidas por Python y Scala | E3 exige la misma protección en histórico y tiempo real; así no se duplican | Javier Saguar | Vigente |
| 17/09/2026 | El trabajo se hace dentro de WSL2 (Ubuntu) con Docker; la parte 1 sigue en Windows | Las herramientas son de Linux y la webcam solo va bien en Windows | Equipo | Vigente |
| 17/09/2026 | La integración gestos ↔ chatbot es la última fase | Es opcional en el enunciado (diapositiva 5) | Equipo | Vigente |

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
