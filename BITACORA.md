# Bitácora del proyecto

Registro de cambios escrito por personas, no por Git. Sirve para dos cosas:

1. Que cualquiera del equipo sepa qué ha pasado sin leerse el código ni los commits.
2. Que cualquier asistente de IA que retome el trabajo (Claude, ChatGPT, Gemini, Copilot…) tenga el
   contexto al día y no reinvente ni deshaga lo ya decidido.

## Cómo se usa

- **Antes de trabajar:** lee «Estado actual», «Decisiones tomadas» y las dos o tres últimas entradas.
  Si vas a usar una IA, dale este fichero completo como primer contexto.
- **Al terminar, antes del commit o del *pull request*:** añade una entrada nueva **arriba** de la
  lista, con la plantilla, y actualiza «Estado actual».
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
| **Funciona y está probado** | Reglas de esquema y privacidad (Python y Scala), APIs de captura y acceso (56 tests), validación del `docker-compose` con todos los perfiles, parte 1 completa (96,5 % LOPO) |
| **Escrito pero sin probar en ejecución** | Trabajos Spark (sin compilar), DAG de Airflow, panel de Grafana, chatbot con Ollama, cliente de gestos |
| **Sin empezar** | Medición de las 3 métricas de calidad, alertas en Grafana, integración de gestos en la demo, vídeo y presentación |
| **Cómo levantarlo** | En Ubuntu (WSL2): `make entorno && make sync && make test && make nucleo` |
| **Pendiente inmediato** | Construir las imágenes (≈10 GB de descargas), compilar el Scala con `make test-spark` y hacer la primera carga con `make airflow && make historico-muestra` |
| **Requisitos por instalar** | NVIDIA Container Toolkit en WSL, para que Ollama use la GPU (si no: `make chatbot SIN_GPU=1`) |

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
