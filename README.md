# PIDS 26/27 · Proyecto 1

[![CI](https://github.com/javiersaguar/PIDS-Proyecto1/actions/workflows/ci.yml/badge.svg)](https://github.com/javiersaguar/PIDS-Proyecto1/actions/workflows/ci.yml)

Plataforma de datos para una empresa de taxis (viajes de taxi amarillo de Nueva York, 2020) con dos chatbots
para consultarla, bajo el escenario **E3: privacidad total**, e integración con el reconocimiento de gestos de
la parte 1.

| Parte | Qué es | Carpeta |
|---|---|---|
| 1 | Reconocimiento de gestos con MediaPipe | [`parte1_gestos/`](parte1_gestos/) |
| 2 | Plataforma: captura, procesado, almacenamiento, acceso y visualización | [`parte2_plataforma/`](parte2_plataforma/) |
| 3 | Chatbot con LLM local (Ollama) que consulta la plataforma | [`parte3_chatbot/`](parte3_chatbot/) |
| 3 bis | Chatbot RAG: LangChain + Qdrant + LLM externo en la UE (Helmcode) | [`parte3_chatbot_rag/`](parte3_chatbot_rag/) |
| — | Integración gestos ↔ plataforma ↔ chatbot (última fase) | [`integracion/`](integracion/) |

## Stack tecnológico

**Plataforma de datos**

![Spark](https://img.shields.io/badge/Spark-4.0.4-E25A1C?logo=apachespark&logoColor=white)
![Scala](https://img.shields.io/badge/Scala-2.13-DC322F?logo=scala&logoColor=white)
![Redpanda](https://img.shields.io/badge/Redpanda-25.2%20%C2%B7%20API%20Kafka-E5322D?logo=apachekafka&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-8.0-47A248?logo=mongodb&logoColor=white)
![SeaweedFS](https://img.shields.io/badge/SeaweedFS-4.47%20%C2%B7%20S3-2E7D32)
![Airflow](https://img.shields.io/badge/Airflow-3.3-017CEE?logo=apacheairflow&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-3.1-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-11.5-F46800?logo=grafana&logoColor=white)

**APIs y chatbots**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.13-E92063?logo=pydantic&logoColor=white)
![Chainlit](https://img.shields.io/badge/Chainlit-2.12-F80061)
![Ollama](https://img.shields.io/badge/Ollama-llama3.1%3A8b-000000?logo=ollama&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.4-1C3C3C?logo=langchain&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-1.19-DC244C?logo=qdrant&logoColor=white)
![Helmcode](https://img.shields.io/badge/Helmcode-deepseek--v4--flash%20%C2%B7%20UE-0F6FFF)

**Reconocimiento de gestos**

![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-0097A7?logo=mediapipe&logoColor=white)
![Keras](https://img.shields.io/badge/Keras-3-D00000?logo=keras&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.10%20%C2%B7%20CUDA-EE4C2C?logo=pytorch&logoColor=white)

**Despliegue y calidad**

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![uv](https://img.shields.io/badge/uv-0.12-DE5FE9?logo=uv&logoColor=white)
![pytest](https://img.shields.io/badge/pytest%20%C2%B7%20ScalaTest-tests-0A9EDC?logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

Por qué cada tecnología: [`docs/comparativa.md`](docs/comparativa.md). Arquitectura: [`docs/arquitectura.md`](docs/arquitectura.md).

## E3 en una frase

Los viajes individuales solo existen en una zona restringida (S3 y la cola de eventos) a la que solo
acceden la ingesta y Spark. Lo consultable son **agregados** con los grupos de menos de 10 viajes
ocultos, y la única puerta es una API que rechaza cualquier consulta individual, propone una
alternativa y lo registra todo. Los dos chatbots solo ven esos agregados; el RAG los envía, junto con la
pregunta, a un LLM que se ejecuta en la UE sin registro de datos, y el de Ollama no saca nada del equipo.
Detalle en [`docs/escenario_E3.md`](docs/escenario_E3.md) y, para el chatbot RAG,
[`parte3_chatbot_rag/CONTRATOS.md`](parte3_chatbot_rag/CONTRATOS.md).

```mermaid
flowchart LR
    G[Gestos · Windows] -.-> CAP[API captura]
    SIM[Simulador] --> CAP --> RP[[Redpanda]] --> SP[Spark]
    AF[Airflow] --> S3[(S3 crudo)] --> SP
    SP --> S3
    SP --> MG[(MongoDB · agregados)] --> ACC[API acceso<br/>filtro de privacidad]
    ACC --> BOT[Chatbot · Ollama]
    ACC --> RAG[Chatbot RAG · LangChain]
    ACC -- indexador --> QD[(Qdrant)] --> RAG
    RAG -.-> HC[Helmcode · LLM en la UE]
    ACC --> PR[Prometheus] --> GR[Grafana]
    CAP -. SSE .-> BOT
```

## Puesta en marcha

Dentro de Ubuntu (WSL2), en la raíz del repositorio (requisitos en [`docs/herramientas.md`](docs/herramientas.md)):

```bash
make entorno              # genera .env con claves aleatorias (make entorno-completar si ya tenías uno)
make sync && make test    # entorno Python y tests
make nucleo               # S3, Redpanda, MongoDB y APIs
make airflow              # + Spark y Airflow
make historico-muestra    # carga el CSV de muestra (Airflow → Spark → MongoDB)
make observabilidad       # + Prometheus y Grafana
make chatbot              # + Ollama y chatbot local (SIN_GPU=1 si no hay GPU NVIDIA)
make rag-comprobar        # comprueba el proveedor del LLM externo (pega antes LLM_API_KEY en .env)
make chatbot-rag          # + Qdrant y chatbot RAG
make rag-indexar          # indexa en Qdrant el conocimiento y las fichas de agregados
make tiempo-real          # arranca el streaming en Spark
make simular              # envía viajes a la API de captura
make                      # lista de todos los comandos
```

| Servicio | URL |
|---|---|
| Chatbot (Ollama) | http://localhost:8010 |
| Chatbot RAG | http://localhost:8011 |
| Airflow | http://localhost:8085 |
| Grafana | http://localhost:3000 |
| Spark | http://localhost:8090 |
| Qdrant | http://localhost:6333/dashboard |
| API de acceso | http://localhost:8002/docs |
| API de captura | http://localhost:8001/docs |

Las contraseñas y claves están en `.env`. La única que no se genera sola es `LLM_API_KEY`, la del proveedor
del LLM externo, que se pega a mano desde el panel de Helmcode.

## Estructura

```
├── config/                  reglas compartidas Python/Scala: esquema del viaje y privacidad
├── data/muestra/            los 999 viajes de ejemplo (el resto de datos no se versiona)
├── docker/                  imagen común de los servicios Python
├── docs/                    plan, arquitectura, comparativa, E3, métricas, casos de uso, datos
├── parte1_gestos/
├── parte2_plataforma/
│   ├── comun/               esquema y reglas de privacidad (Python)
│   ├── captura/             API de entrada de eventos
│   ├── acceso/              API de consulta con filtro de privacidad
│   ├── spark/               trabajos Scala: CargaHistorica y TiempoReal
│   ├── airflow/             imagen y DAG
│   ├── s3/  mongodb/        inicialización del almacenamiento
│   ├── simulador/           reenvío de viajes como tiempo real
│   └── observabilidad/      Prometheus y Grafana
├── parte3_chatbot/          Chainlit + Ollama: agente, herramientas y barreras sobre las cifras
├── parte3_chatbot_rag/      Chainlit + LangChain + Qdrant + Helmcode; reutiliza las herramientas y
│                            barreras del anterior. CONTRATOS.md reparte el trabajo en cinco bloques
├── integracion/             cliente de gestos (Windows)
├── scripts/                 descarga, perfilado, generación de .env, auditoría, latencia y ataques
├── tests/                   tests de Python (los de Scala están en parte2_plataforma/spark)
├── docker-compose.yml       perfiles: spark, airflow, observabilidad, chatbot, rag, rag-indexar,
│                            herramientas, simulador
└── Makefile
```

## Equipo y ramas

Cada persona trabaja en su propia rama y lleva sus cambios a `main` con un *pull request*; nadie sube
directamente a `main`. Así no nos pisamos el trabajo.

| Persona | Rama | Responsabilidad principal |
|---|---|---|
| Javier Saguar | `javier-saguar` | Spark (Scala): histórico y tiempo real; parte 1 |
| Alejandro Cuevas | `alejandro-cuevas` | Almacenamiento, cola y despliegue (Compose, S3, MongoDB, Redpanda) |
| Mónica Fernández | `monica-fernandez` | APIs y reglas de privacidad |
| Pedro José Orrego | `pedro-jose-orrego` | Airflow, Prometheus, Grafana y métricas de calidad |
| Daniel Naval | `daniel-naval` | Chatbot, casos de uso e integración con los gestos |

Reparto completo en [`docs/plan.md`](docs/plan.md).

```bash
git fetch origin
git switch <tu-rama>          # la primera vez la crea a partir de origin/<tu-rama>
git merge origin/main         # al empezar el día y antes de abrir el pull request
git push origin <tu-rama>     # y el pull request, de <tu-rama> a main
```

Para una tarea larga puedes abrir una rama de tarea (`tarea/...`) a partir de la tuya. El chatbot RAG se
construye así: la rama `tarea/rag-base` lleva la infraestructura y cada bloque (`rag/2-corpus`,
`rag/3-agente`, `rag/4-interfaz`, `rag/5-privacidad`) se fusiona en ella antes del *pull request* a `main`;
el reparto de ficheros y las firmas están en [`parte3_chatbot_rag/CONTRATOS.md`](parte3_chatbot_rag/CONTRATOS.md).

## Cómo trabajamos

Dos ficheros llevan el día a día del proyecto. **Léelos antes de ponerte a trabajar** y, si usas un
asistente de IA, pásaselos como primer contexto: así nadie trabaja con información desactualizada.

| Fichero | Para qué |
|---|---|
| [`TAREAS.md`](TAREAS.md) | Las **10 tareas siguientes**, en orden, con qué hay que hacer y cuándo se considera terminada. Coges una, pones tu nombre y la marcas al acabar |
| [`BITACORA.md`](BITACORA.md) | Qué se ha hecho ya: cada cambio con su motivo, cómo comprobarlo y qué quedó pendiente. Incluye el estado actual del proyecto y las decisiones tomadas |

Cada cambio termina con una entrada en la bitácora y su tarea actualizada; los *pull requests* lo
recuerdan con una casilla.
