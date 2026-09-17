# Datos

## Fuentes

| Fuente | Qué es | Uso |
|---|---|---|
| [2020 Yellow Taxi Trip Data](https://data.cityofnewyork.us/Transportation/2020-Yellow-Taxi-Trip-Data/kxp8-n2sj/about_data) | 24 648 499 viajes, 18 columnas (NYC Open Data, API SODA) | Enunciado; `scripts/descargar_datos.py --fuente api` |
| Parquet mensual de la TLC | Los mismos viajes, un fichero por mes (~90 MB) | Airflow y `make descargar` |
| `taxi_zone_lookup.csv` de la TLC | Zona → barrio y nombre (265 zonas) | **Fuente nueva**: permite agregar por barrio y buscar zonas por nombre |
| Muestra de Moodle | 999 viajes | Tests y pruebas rápidas |

Cada fuente trae un formato distinto (nombres en mayúsculas o minúsculas, fechas en 12 h, ISO o
timestamp); `config/esquema_viaje.json` los unifica.

## Diccionario

| Columna original | Canónica | Descripción |
|---|---|---|
| VendorID | vendor_id | Proveedor del taxímetro: 1 Creative Mobile Technologies, 2 VeriFone |
| tpep_pickup_datetime | recogida | Inicio del viaje |
| tpep_dropoff_datetime | llegada | Fin del viaje |
| passenger_count | pasajeros | Pasajeros (lo introduce el conductor) |
| trip_distance | distancia_millas | Distancia en millas |
| RatecodeID | tarifa_id | 1 estándar, 2 JFK, 3 Newark, 4 Nassau/Westchester, 5 negociada, 6 compartido |
| store_and_fwd_flag | almacenado_y_reenviado | Y si el registro se guardó en el vehículo antes de enviarse |
| PULocationID / DOLocationID | zona_origen / zona_destino | Zona de taxi (1–265) |
| payment_type | tipo_pago | 1 tarjeta, 2 efectivo, 3 sin cargo, 4 disputa, 5 desconocido, 6 anulado |
| fare_amount | tarifa | Tarifa del taxímetro (USD) |
| extra, mta_tax, improvement_surcharge, congestion_surcharge | extra, impuesto_mta, recargo_mejora, recargo_congestion | Recargos |
| tip_amount | propina | Propina (solo registrada con tarjeta) |
| tolls_amount | peajes | Peajes |
| total_amount | importe_total | Importe total cobrado |

## Calidad observada en la muestra (`make datos-muestra`)

- 999 viajes, 8 rechazados (0,8 %): 3 fuera de 2020 (diciembre de 2019), 4 importes negativos
  (reembolsos) y 1 con duración no positiva.
- Avisos que no invalidan: 21 viajes con 0 pasajeros y 9 con distancia 0.
- 82 zonas de origen distintas en cinco horas: la mayoría de grupos por hora y zona tienen menos de 10
  viajes y quedan suprimidos, así que la muestra sirve para probar el enmascarado.
