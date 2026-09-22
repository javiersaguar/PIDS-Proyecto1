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

Las reglas son las de [`escenario_E3.md`](escenario_E3.md) y `config/privacidad.json`.

## Qué se publica en el anfitrión

Solo servicios con credencial:

| Servicio | URL | Credencial |
|---|---|---|
| Portal | http://localhost:8020 | `FRONTEND_CLAVE` |
| Chatbot y chatbot RAG | http://localhost:8010 y :8011 | `CHATBOT_USUARIO` / `CHATBOT_CLAVE`. La sesión la firma `CHAINLIT_AUTH_SECRET` |
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
