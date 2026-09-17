# Datos

Solo se versiona `muestra/yellow_tripdata_2020_muestra.csv` (999 viajes del ejemplo de Moodle).
El resto no se sube al repositorio.

- `make descargar MES=2020-01` deja el Parquet del mes y la tabla de zonas en `data/crudo/`
  (para perfilar o simular en local).
- En la plataforma, Airflow descarga los meses directamente al bucket S3 `crudo`.

Diccionario de datos y calidad observada: [`../docs/datos.md`](../docs/datos.md).
