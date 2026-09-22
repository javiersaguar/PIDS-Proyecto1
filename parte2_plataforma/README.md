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
| `observabilidad/` | Prometheus y los ocho cuadros de Grafana | Prometheus, Grafana |

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
`pids-tiempo-real` en marcha (el script lo comprueba dentro del contenedor de Spark: la interfaz no se publica) y deja la evidencia en `informes/latencia-*`.

Los viajes sintéticos son válidos, llevan un lote `latencia-...` y se quedan en el archivo restringido
(`s3://crudo/validos/tiempo_real`) y en `publico.tr_viajes_hora_zona`. Cuidado: al usar horas de finales de 2020
adelantan la *watermark* del streaming (2 h por detrás del viaje más reciente). Mientras el trabajo de tiempo
real conserve ese estado, los viajes anteriores, como los de la muestra del 1 de enero, no se agregan (sí se
archivan). `make tiempo-real-reiniciar` lo deja desde cero (sección siguiente).

## Tiempo real desde cero y captura en directo

```bash
make tiempo-real-reiniciar       # para el trabajo, borra su checkpoint, recorta la cola, vacía tr_* y lo relanza
make captura-preparar            # una vez: diciembre de 2020 de la TLC, un CSV.gz por día en data/directo/
make capturar                    # captura en directo desde el portal (VELOCIDAD=60: una hora de 2020 por minuto)
make capturar-parar
```

**Reiniciar** (`scripts/reiniciar_tiempo_real.py`, T11) hace, en orden: matar el driver supervisado de
`pids-tiempo-real` (si no, el máster lo relanzaría con el checkpoint viejo), borrar
`/opt/spark/checkpoints/tiempo_real`, recortar `viajes-crudos` hasta el final (el trabajo lee desde el principio y
volvería a ver los mismos viajes; ya están archivados en `s3://crudo/validos/tiempo_real`), vaciar
`publico.tr_*` con el administrador de MongoDB y relanzar. Pide confirmación (`ARGS=--si` para no hacerlo). El
histórico no se toca. Tarda unos 30 s.

**La captura en directo** (`parte2_plataforma/simulador/directo.py`) reproduce viajes reales de 2020 contra la API
de captura con un reloj simulado: en cada segundo envía los viajes cuya recogida ya ha pasado. Spark los agrega por
hora de recogida, así que Tiempo real avanza hora a hora (a ×60, una por minuto). La lleva el portal (botón
«Capturar datos» del grafo, `POST /api/operaciones/captura`), que recuerda por dónde va; `make capturar` se lo pide
a él para que nunca haya dos emisores a la vez, que repetirían viajes. Si el portal se reinicia, sigue en la hora
siguiente a la última que Spark haya publicado. Cuando llega al 31/12, para volver a empezar: reiniciar.

Medido el 22/09 tras reiniciar: 41 608 viajes del 1 de diciembre enviados a ×600 (diez horas de 2020 por minuto,
entre 48 y 230 viajes por segundo) y agregados por Spark hora a hora (de 11 viajes visibles a las 02:00 a 7 464 a las
13:00, esta última con repetidos de una prueba, que llevó a dejar un solo emisor).

## Alta disponibilidad de la API de acceso

`acceso` (puerto 8002) es un proxy Caddy delante de dos réplicas iguales, `acceso-a` y `acceso-b`. Si una cae, la
otra atiende todo y los clientes no lo notan. Detalle, medidas y límites del resto de componentes en
[`docs/arquitectura.md`](../docs/arquitectura.md#alta-disponibilidad).

```bash
make alta-disponibilidad                  # carga continua mientras para, tira y recupera cada réplica
docker compose stop acceso-a              # a mano: la API sigue respondiendo (cabecera X-Replica: acceso-b)
docker compose start acceso-a
docker compose up -d --no-deps acceso-a acceso-b   # tras cambiar ACCESO_CLAVES en .env: las dos réplicas
```

## Probar las APIs a mano

```bash
source .env
curl -s -X POST localhost:8002/consultas -H "X-API-Key: $ACCESO_CLAVE_EQUIPO" \
  -H 'Content-Type: application/json' \
  -d '{"nivel": "dia_barrio", "desde": "2020-01-01T00:00:00", "hasta": "2020-01-02T00:00:00"}'

curl -s localhost:8002/viajes/123 -H "X-API-Key: $ACCESO_CLAVE_EQUIPO"   # siempre 403
```
