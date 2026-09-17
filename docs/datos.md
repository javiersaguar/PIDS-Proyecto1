# Datos

## Fuentes

| Fuente | Qué es | Uso |
|---|---|---|
| [2020 Yellow Taxi Trip Data](https://data.cityofnewyork.us/Transportation/2020-Yellow-Taxi-Trip-Data/kxp8-n2sj/about_data) | 24 648 499 viajes, 18 columnas (NYC Open Data, API SODA) | Enunciado; `scripts/descargar_datos.py --fuente api` |
| Parquet mensual de la TLC | Los mismos viajes, un fichero por mes (~90 MB) | Airflow y `make descargar` |
| `taxi_zone_lookup.csv` de la TLC | Zona → barrio y nombre (265 zonas) | **Fuente nueva**: permite agregar por barrio y buscar zonas por nombre |
| Muestra de Moodle | 999 viajes | Tests y pruebas rápidas |

## La misma columna, cuatro formatos

Es el problema de calidad más llamativo que nos hemos encontrado: **el mismo dataset llega en formatos
distintos según por dónde se descargue**, y `config/esquema_viaje.json` los unifica.

| Fuente | Nombres | Fecha de recogida | Distancia |
|---|---|---|---|
| Muestra de Moodle | `VendorID` | `01/01/2020 12:28:15 AM` | `1.2` |
| Exportación completa (botón «Export» de NYC Open Data) | `"VendorID"` | `2020 Jan 01 12:28:15 AM` | `1,2` |
| API SODA | `vendorid` | `2020-01-01T00:28:15.000` | `1.20` |
| Parquet de la TLC | `VendorID` | timestamp | 1.2 (double) |

La exportación completa sale con **formato europeo**: el mes abreviado en la fecha y la **coma como
separador decimal** (con el punto como separador de miles). La primera carga del año completo rechazó
los 24 648 499 viajes por «falta un campo obligatorio», porque todos los números quedaban vacíos.

La normalización acepta ahora los cuatro formatos, y hay dos ficheros de muestra en `data/muestra/`
(uno de cada formato de texto) con tests en Python y en Scala que comprueban que dan el mismo viaje.

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
