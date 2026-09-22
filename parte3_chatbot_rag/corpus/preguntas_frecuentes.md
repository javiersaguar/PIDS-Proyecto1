# Preguntas frecuentes sobre los datos y la privacidad

## ¿Qué datos hay?

Los viajes de taxi amarillo de Nueva York durante todo 2020 (unos 24,6 millones de viajes, de los que
el 96 % superan la validación), publicados en la fuente `historico`, y los viajes que van llegando por el
flujo de tiempo real, publicados en la fuente `tiempo_real` con las mismas reglas. Los importes están en
dólares y las distancias en millas.

## ¿Por qué algunos grupos aparecen como «oculto»?

La plataforma sigue el escenario de **privacidad total (E3)**: ningún dato individual puede exponerse.
Solo se publican agregados. Los grupos con menos de 10 viajes (el umbral k) se publican sin cifras, y
también algunos con 10 o más: es la **supresión complementaria**, que impide deducir un grupo pequeño
restando los visibles al total del día. La API no distingue unos de otros (esa marca no se publica), así
que todos salen como «oculto». Así se distingue «no hubo viajes» (no aparece la fila) de «el grupo está
oculto». Un grupo enmascarado nunca se estima, no se confirma ni se descarta ningún valor y no se suma a
ningún total. No se escribe «<10»: para los complementarios sería falso.

## ¿Qué diferencia hay entre una zona y un barrio?

La Comisión de Taxis de Nueva York (TLC) divide la ciudad en **265 zonas de taxi** (`LocationID` 1 a 265),
cada una dentro de un **barrio** (*borough*): Manhattan, Brooklyn, Queens, Bronx y Staten Island. La tabla
de zonas añade tres valores especiales de barrio: `EWR` para el aeropuerto de Newark (zona 1, en Nueva
Jersey); `Unknown`, el barrio de la zona 264 («N/A»: viajes sin localización registrada); y `N/A`, el barrio
de la zona 265 («Outside of NYC»: viajes fuera de la ciudad). Por zona solo se publica el nivel por horas
(`hora_zona`); por barrio se publican el día (`dia_barrio`) y los flujos entre barrios (`od_dia_barrio`).

## ¿Qué zonas son los aeropuertos?

- **JFK Airport**, zona 132, barrio Queens.
- **LaGuardia Airport**, zona 138, barrio Queens.
- **Newark Airport**, zona 1, barrio EWR.

Times Square es la zona **Times Sq/Theatre District** (230, Manhattan); Wall Street está en **Financial
District North y South** (87 y 88, Manhattan); Penn Station es **Penn Station/Madison Sq West** (186,
Manhattan); Central Park es la zona 43 (Manhattan). Harlem tiene varias zonas (Central Harlem, Central Harlem
North, East Harlem North, East Harlem South).

## ¿Qué es un flujo?

Un flujo es el número de viajes que salieron de un barrio y llegaron a otro (o al mismo) en un día: el nivel
`od_dia_barrio`. Es la única forma de preguntar por el destino, y siempre por barrio y por día completo. No se
publican destinos por zona ni por hora.

## ¿Qué significan las métricas?

- `n_viajes`: número de viajes del grupo.
- `distancia_media`: media de la distancia recorrida, en millas.
- `importe_medio`: media del importe total cobrado, en dólares (tarifa, recargos, peajes y propina).
- `propina_media`: media de la propina, en dólares. Las propinas en efectivo no quedan registradas, así que
  la propina media es la de los pagos con tarjeta repartida entre todos los viajes.
- `pct_pago_tarjeta`: porcentaje de viajes pagados con tarjeta de crédito (`payment_type` 1 en la TLC).

Todas las medias se redondean a dos decimales y no se publican para los grupos enmascarados.

## ¿Qué pasa con la información de una consulta rechazada?

Cada consulta a la API de acceso queda registrada en una auditoría de solo inserción con su resultado
(permitida, enmascarada o rechazada), los motivos y la alternativa propuesta. Un rechazo no es un error:
es la plataforma protegiendo un dato individual y proponiendo la consulta agregada más parecida.

## ¿De dónde salen las cifras del asistente?

Siempre de la API de acceso, en el mismo turno de conversación: cada número de una respuesta tiene que
aparecer en las filas o en el resumen que devuelve la plataforma. El asistente no calcula, no estima y no
recuerda cifras de otras conversaciones; las fichas de agregados recuperadas como contexto se obtuvieron
también por esa API y llevan la misma protección.
