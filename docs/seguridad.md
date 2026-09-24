# Seguridad y modelo de amenazas

Escenario E3: ningún viaje individual sale de la zona restringida. Este documento dice a quién se tiene
en cuenta, qué está cerrado con credencial y qué se deja fuera a propósito.

## A quién se considera

Otra persona o proceso en el mismo equipo, o un navegador abierto en `localhost`. Los puertos que se
publican van solo a `127.0.0.1`, así que desde otra máquina de la red no se llega. No se considera
atacante a quien ya tiene el daemon de Docker: con `docker compose exec` ve lo mismo que el operador.

No se modela un atacante de internet ni un robo de la clave de Helmcode fuera de este equipo. Eso está
en la decisión del LLM externo ([`chatbot_rag.md`](chatbot_rag.md), T13).

## Qué se protege

| Dato | Dónde vive | Quién entra |
|---|---|---|
| Viajes individuales | S3 `crudo` y el topic `viajes-crudos` | Spark y la ingesta, con clave propia. Kafka no se publica |
| Agregados | MongoDB `publico` | La API de acceso, con `X-API-Key`. Grupos por debajo de k van vacíos |
| Auditoría | MongoDB `auditoria` | Spark y la API solo insertan. `pids_auditor` solo lee |
| Secretos | `.env` (no está en Git, modo `0600`) | Cada componente tiene la suya |
| Imagen de la cámara (gestos) | El navegador o el equipo con la demo de Windows | Nadie más: a la plataforma solo llegan la etiqueta y la confianza, por la API de captura con la clave del cliente `gestos` (en el portal, la guarda el BFF) |

Las reglas son las de [`escenario_E3.md`](escenario_E3.md) y `config/privacidad.json`.

## Qué se publica en el anfitrión

Solo servicios con credencial:

| Servicio | URL | Credencial |
|---|---|---|
| Portal | http://localhost:8020 | `FRONTEND_CLAVE` |
| Chatbot y chatbot RAG | http://localhost:8010 y :8011 (`PUERTO_CHATBOT_RAG`) | `CHATBOT_USUARIO` / `CHATBOT_CLAVE`. La sesión la firma `CHAINLIT_AUTH_SECRET` |
| Airflow | http://localhost:8085 | `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` |
| Grafana | http://localhost:3000 | Ver los cuadros no pide clave (solo `127.0.0.1`; el portal lee de ahí el estado de las alertas). Editar sigue siendo `admin` / `GRAFANA_ADMIN_PASSWORD`. El alta pública está cerrada |
| API de acceso y de captura | :8002 y :8001 | Cabecera `X-API-Key` |
| MongoDB | `localhost:27018` | Usuario y contraseña. Sin ellas, `listDatabases` responde 13 |
| S3 | http://localhost:8333 | Clave de acceso. Sin ella responde 403 |

## Qué no se publica

No tienen login y ven datos o pueden lanzar trabajo. Se usan por el nombre del contenedor:

| Servicio | Por qué no sale del Docker |
|---|---|
| Pasarela REST de Spark (`6066`) y su interfaz (`8080`) | Airflow y `spark-submit` hablan con `spark-master` dentro de la red. `make latencia` lee la interfaz con `docker compose exec` |
| Interfaces de los workers | Misma razón |
| Kafka (`19092` / `9092`) | El topic `viajes-crudos` lleva viajes individuales y Redpanda va sin SASL |
| Consola de Redpanda | Enseña esos mensajes. `make herramientas` la arranca, pero no abre puerto |
| Prometheus | Grafana y el portal lo consultan en `prometheus:9090`. El portal solo ejecuta las consultas de los JSON de los cuadros: desde el navegador (o por el túnel) se pide un cuadro por su nombre, nunca una consulta de PromQL |
| Ollama | El chatbot lo usa en `ollama:11434` |
| Qdrant | El índice lo leen el chatbot RAG y el portal en `qdrant:6333` |
| Máster, filer y volúmenes de SeaweedFS (`9333`, `8888`, `8080`) | La API del máster borra colecciones sin credencial, y el filer y los volúmenes sirven los ficheros de `crudo` |

## Mirarlas un rato: `make ver`

Para enseñar o depurar, cuatro de esas interfaces se pueden abrir **solo mientras se miran**, en
`127.0.0.1` y **de solo lectura**. `make ver` levanta un proxy aparte (servicio `ver`, perfil `ver`, Caddy con
[`docker/ver/Caddyfile`](../docker/ver/Caddyfile)) y `make ver-cerrar` lo quita. Como es un contenedor aparte,
abrirlas no reinicia ningún servicio: el tiempo real sigue en marcha. `make parar` también lo cierra.

| Interfaz | En el anfitrión | Qué deja el proxy |
|---|---|---|
| Prometheus | http://localhost:9091 (`PUERTO_PROMETHEUS`; el 9090 lo suele ocupar otro Prometheus) | Consultas y objetivos. Nada de `/api/v1/admin/*` ni `/-/*` |
| Spark | http://localhost:8090 | Solo `GET`: máster, workers y trabajos, sin los botones *kill*. Los valores con claves o URI salen tapados (`spark.redaction.regex`) |
| Qdrant | http://localhost:6333/dashboard | Leer y buscar. Nada de `PUT`, `PATCH`, `DELETE`, borrados por `POST` ni alias |
| SeaweedFS | http://localhost:9333 | Solo la página de estado del máster: volúmenes, colecciones y tamaños, **sin nombres de ficheros**. El resto de su API, `403` |

Lo que lleva viajes individuales **no se abre nunca**, ni con `make ver`: Kafka, la consola de Redpanda y el
filer o los volúmenes de SeaweedFS (E3). Ollama tampoco: es una API sin interfaz.

`make localhost` lista todas las direcciones, las publicadas y las de `make ver`, y dice cuáles responden
(`ARGS=--abrir` las abre en el navegador). Solo lee las variables `PUERTO_*` de `.env`: no imprime ninguna
clave, solo el nombre de la variable que la guarda.

## Qué queda fuera

- `GET /salud`, `GET /metrics` y `/docs` de las dos APIs no piden clave. `/metrics` lleva contadores y
  totales ya agregados (los del panel), no un viaje. Cerrarlas obligaría a dar de alta a Prometheus
  como cliente de la API.
- Quien administra Docker ve los ficheros de los volúmenes y los logs de los workers.
- El chatbot RAG envía la pregunta y agregados ya protegidos a Helmcode si el grupo mantiene T13.
- La demostración de Vercel no conecta con esta plataforma: son datos grabados y enmascarados.
- `make frontend-dev` (el BFF en el anfitrión) no alcanza Prometheus, Ollama ni Qdrant. El portal
  que sí los usa es `make frontend`, dentro de Docker.

## Rotación de claves

`make entorno` no pisa un `.env` que ya existe. GNU make no acepta `make entorno --forzar` (lo toma
como opción suya). El comando que regenera es:

```bash
make entorno FORZAR=1
```

Eso llama a `scripts/generar_env.py --forzar`, cambia las claves aleatorias y deja `LLM_API_KEY`
vacía para pegarla otra vez. Las claves nuevas no entran solas en lo que ya está inicializado:

| Volumen | Hay que recrearlo | Por qué |
|---|---|---|
| `pids_mongo-datos` | Sí | Los usuarios se crean una vez, en `01_usuarios.js` |
| `pids_airflow-db` | Sí | La contraseña de PostgreSQL y el usuario de Airflow quedan en el volumen |
| `pids_grafana-datos` | Sí | Grafana solo aplica `GF_SECURITY_ADMIN_PASSWORD` al crear la base |
| `pids_s3-datos` | No | Las claves se escriben en la configuración al arrancar el contenedor |
| El resto | No | No guardan estas contraseñas |

Recrear esos tres volúmenes borra los agregados, la auditoría, el estado de Airflow y los paneles
que no estén en los ficheros de provisión. Los viajes en S3 se quedan. Después hay que levantar de
nuevo y repetir la carga histórica. Comprobado el 22/09 con un MongoDB desechable y el mismo
`01_usuarios.js`: sin borrar el volumen la contraseña vieja sigue valiendo; con el volumen nuevo
solo entra la nueva, y sin contraseña `listDatabases` sigue en 13.

```bash
docker compose --profile airflow --profile observabilidad down
docker volume rm pids_mongo-datos pids_airflow-db pids_grafana-datos
docker compose --profile airflow --profile observabilidad up -d
```

No hace falta tocar `pids_s3-datos`: basta con recrear el contenedor `s3` para que lea las claves nuevas.
