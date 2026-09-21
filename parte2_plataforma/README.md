# Parte 2 · Plataforma de datos

| Carpeta | Servicio | Tecnología |
|---|---|---|
| `comun/` | Esquema canónico y reglas de privacidad (Python) | pandas, Pydantic |
| `captura/` | API de entrada: viajes, gestos y SSE de gestos | FastAPI + aiokafka |
| `acceso/` | API de consulta con filtro de privacidad y auditoría | FastAPI + PyMongo |
| `spark/` | `pids.CargaHistorica` (lotes) y `pids.TiempoReal` (streaming) | Spark 4.0.4, Scala 2.13 |
| `airflow/` | DAG `pids_carga_historica` | Airflow 3.3 |
| `s3/` | Arranque de SeaweedFS con identidades y creación de buckets | SeaweedFS, boto3 |
| `mongodb/` | Usuarios, roles e índices | MongoDB 8 |
| `simulador/` | Reenvía un fichero de viajes como eventos en tiempo real | requests |
| `observabilidad/` | Configuración de Prometheus y panel de Grafana | Prometheus, Grafana |

## Spark

- Tests: `make test-spark` (compila y ejecuta ScalaTest dentro de Docker).
- Lanzar a mano, desde el máster:
  - `/opt/pids/lanzar.sh TiempoReal`: streaming supervisado;
  - `/opt/pids/lanzar.sh CargaHistorica s3a://crudo/muestra/yellow_tripdata_2020_muestra.csv muestra`.
- Para editar el código con autocompletado: abre `parte2_plataforma/spark` en VS Code con la extensión
  Metals (instala sbt y Java por su cuenta).

## Auditoría de privacidad

`make auditoria` responde «¿qué se ha rechazado hoy y por qué?» con el usuario de solo lectura `pids_auditor`:
decisiones por resultado y por cliente, motivos de rechazo más frecuentes, rechazos recientes y cargas.

```bash
make auditoria                                                     # últimas 24 h, por pantalla
make auditoria ARGS="--horas 8 --salida informes/auditoria.md"     # también a fichero (informes/ no se versiona)
make auditoria ARGS="--comprobar-permisos"                         # demuestra que la auditoría es de solo añadir
```

`--comprobar-permisos` intenta un insert y un delete con `pids_auditor`, y un update y un delete con
`pids_acceso`, sobre `auditoria.decisiones`. Las cuatro operaciones están hechas para no cambiar nada aunque los
permisos estuvieran mal (condiciones imposibles, un `_id` que ya existe) y solo se da por buena la denegación con
el código 13 (*Unauthorized*) de MongoDB.

## Latencia del tiempo real

`make latencia` mide cuánto tarda un viaje en ser consultable (métrica M3): envía 20 lotes de 15 viajes por la
API de captura, cada uno a una hora y zona nuevas (por defecto, horas del 31/12/2020 en la zona 265), y consulta
la API de acceso cada segundo hasta que aparece el grupo con sus 15 viajes. Necesita **un único** trabajo
`pids-tiempo-real` en marcha (se comprueba en http://localhost:8090) y deja la evidencia en `informes/latencia-*`.

Los viajes sintéticos son válidos, llevan un lote `latencia-...` y se quedan en el archivo restringido
(`s3://crudo/validos/tiempo_real`) y en `publico.tr_viajes_hora_zona`. Cuidado: al usar horas de finales de 2020
adelantan la *watermark* del streaming (2 h por detrás del viaje más reciente). Mientras el trabajo de tiempo
real conserve ese estado, los viajes anteriores, como los de la muestra del 1 de enero, no se agregan (sí se
archivan). Para la demo, o se simulan viajes posteriores (por ejemplo, un fichero de diciembre), o se relanza el
trabajo con un checkpoint nuevo cuando esos lotes hayan salido del topic (retención de 24 h), porque el trabajo
lee el topic desde el principio.

## Probar las APIs a mano

```bash
source .env
curl -s -X POST localhost:8002/consultas -H "X-API-Key: $ACCESO_CLAVE_EQUIPO" \
  -H 'Content-Type: application/json' \
  -d '{"nivel": "dia_barrio", "desde": "2020-01-01T00:00:00", "hasta": "2020-01-02T00:00:00"}'

curl -s localhost:8002/viajes/123 -H "X-API-Key: $ACCESO_CLAVE_EQUIPO"   # siempre 403
```
