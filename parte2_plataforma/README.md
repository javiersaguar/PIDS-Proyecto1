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

## Probar las APIs a mano

```bash
source .env
curl -s -X POST localhost:8002/consultas -H "X-API-Key: $ACCESO_CLAVE_EQUIPO" \
  -H 'Content-Type: application/json' \
  -d '{"nivel": "dia_barrio", "desde": "2020-01-01T00:00:00", "hasta": "2020-01-02T00:00:00"}'

curl -s localhost:8002/viajes/123 -H "X-API-Key: $ACCESO_CLAVE_EQUIPO"   # siempre 403
```
