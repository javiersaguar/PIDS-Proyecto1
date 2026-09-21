# Guía para traducir preguntas en consultas

Qué publica la plataforma y cómo se pide. Todo lo que aquí se dice se comprueba después en la API de
acceso, que aplica las reglas de privacidad a cada consulta: esta guía sirve para acertar a la primera.

## Los tres niveles de agregación

| Nivel | Dimensiones | Ventana mínima | Para qué preguntas |
|---|---|---|---|
| `hora_zona` | hora y zona de origen (una de las 265 zonas de taxi) | una hora completa | «¿cuántos viajes salieron de JFK entre las 8 y las 12?», «viajes hora a hora desde Times Square» |
| `dia_barrio` | día y barrio de origen (Manhattan, Brooklyn, Queens, Bronx, Staten Island, EWR, N/A, Unknown) | un día completo | «¿qué barrio tuvo más viajes el 3 de marzo?», «propina media en Manhattan en febrero» |
| `od_dia_barrio` | día, barrio de origen y barrio de destino | un día completo | «¿cuántos viajes hubo de Queens a Manhattan el 10 de enero?», «¿a qué barrio fueron más viajes desde el Bronx?» |

El destino solo existe en `od_dia_barrio`, y solo por barrio y día. No hay destino por zona ni por hora:
origen, destino y hora juntos permitirían identificar a una persona.

## Ventanas de tiempo

- Las fechas van en ISO: `2020-03-03T00:00:00`. `desde` se incluye y `hasta` **no** se incluye.
- Un día completo: desde las 00:00 de ese día hasta las 00:00 del día siguiente
  (`2020-03-03T00:00:00` → `2020-03-04T00:00:00`).
- Una franja horaria: «de 8 a 12» son las horas 8, 9, 10 y 11 (`T08:00:00` → `T12:00:00`).
- La medianoche del final del día se escribe como las 00:00 del día siguiente, nunca `T24:00`.
- Las horas van de 00 a 23 y siempre en punto: la granularidad mínima es la hora en `hora_zona` y el día en
  los otros dos niveles. Una pregunta por «las 3:12» se convierte en la hora completa de 03:00 a 04:00.
- El rango máximo por consulta es de **31 días**. Un mes cabe justo; un trimestre necesita tres consultas.
- Los datos son de 2020 (año bisiesto: febrero tiene 29 días; el año, 366). El último instante es el
  31 de diciembre de 2020 a las 23:59, así que `hasta` puede ser `2021-01-01T00:00:00` como máximo.
- «La primera semana de febrero» son los días 1 a 7 (`02-01` → `02-08`); «la segunda semana», del 8 al 14;
  «la primera quincena», del 1 al 15 (`hasta` el 16 a las 00:00).

## Filtros

- Cada filtro admite **un solo valor**. Para comparar barrios o preguntar «cuál tuvo más», se consulta sin
  filtro: llegan todos los barrios (o todas las zonas, o todos los destinos) y se comparan las filas.
- `zona_origen` solo vale en `hora_zona` y admite el identificador (1 a 265) o el nombre («JFK»,
  «Times Square», «LaGuardia»). Si el nombre corresponde a varias zonas, la herramienta `buscar_zona`
  las enumera.
- `barrio_origen` y `barrio_destino` van con el nombre exacto del barrio: `Manhattan`, `Brooklyn`, `Queens`,
  `Bronx` (sin artículo), `Staten Island`, `EWR` (aeropuerto de Newark), `N/A` (zona 265, fuera de la ciudad)
  y `Unknown` (zona 264, sin localización registrada).
- Staten Island, Queens, etc. son barrios, no zonas: para pedir «por horas desde Staten Island» se usa
  `hora_zona` con `barrio_origen`, y se consultan por separado todas las zonas de ese barrio.
- `fuente` es `historico` por defecto; `tiempo_real` cuando la pregunta habla de tiempo real, en directo o
  simulado. Para «la última hora» o «lo que llevamos» existe la herramienta `ultima_hora_con_datos`.

## Métricas

Solo existen cinco, con estos nombres exactos: `n_viajes` (número de viajes), `distancia_media` (millas),
`importe_medio` (dólares), `propina_media` (dólares) y `pct_pago_tarjeta` (porcentaje de viajes pagados con
tarjeta). Las medias se publican redondeadas a dos decimales. No hay número de pasajeros, tarifa, peajes,
proveedor, matrículas, instantes exactos ni destino por zona: pedirlos rechaza la consulta.

## Cómo leer una respuesta

- `filas`: un grupo por fila (una hora y zona, un día y barrio, o un día y par de barrios).
- `resumen`: calculado por la plataforma, no por el modelo: `total_viajes`, `grupo_con_mas_viajes`,
  `grupo_con_menos_viajes` y las medias conjuntas ponderadas por viajes (`propina_media_conjunta`,
  `importe_medio_conjunta`…). Las cifras de una respuesta se copian de aquí o de las filas.
- Un grupo con `n_viajes` igual a `"<10"` está **enmascarado por privacidad**: tuvo menos de 10 viajes, o se
  oculta para que no se pueda deducir otro grupo restando. No tiene cifras, no se suma a ningún total y no se
  estima. Cuando hay grupos enmascarados el resumen no da total ni medias conjuntas.
- `resultado` puede ser `permitida`, `enmascarada` (hay grupos ocultos) o `rechazada` (la consulta viola una
  regla). Un rechazo trae los `motivos` y una `alternativa` que sí se puede responder: se explica y se ofrece.
- `truncada` en verdadero significa que la respuesta tiene más de 500 filas y solo se muestran las primeras:
  conviene acotar la consulta.

## Preguntas que no se pueden responder

Cualquier dato de un viaje, persona, conductor o vehículo concreto: «el viaje de las 3:12», «quién cogió un
taxi», «el trayecto más largo», «cuánto pagó el último pasajero», matrículas, teléfonos, horas exactas de
recogida o llegada. Se usa la herramienta `solicitud_individual` (queda registrado) y se propone una
alternativa agregada: la hora completa de esa zona, o el día completo de ese barrio.
