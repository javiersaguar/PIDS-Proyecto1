# Métricas de calidad propias

El enunciado pide definir 3 métricas relevantes para la restricción y medirlas en la solución.

| # | Métrica | Qué mide | Cómo se mide | Objetivo |
|---|---|---|---|---|
| M1 | **Tasa de fuga de privacidad** | % de peticiones de una batería de preguntas trampa (viajes concretos, horas con minutos, destinos por zona, campos prohibidos…) que devuelven algún dato no agregado o un grupo por debajo de k | Script que lanza la batería contra la API y contra el chatbot y revisa cada respuesta | 0 % |
| M2 | **Utilidad tras la protección** | % de viajes que quedan en grupos publicados (no suprimidos), por nivel | `auditoria.cargas` (Spark registra los grupos publicados y suprimidos de cada carga) | Documentar el equilibrio privacidad–utilidad para k = 5, 10 y 20 |
| M3 | **Latencia de publicación en tiempo real** | Tiempo desde que un viaje entra por `POST /viajes` hasta que su agregado es consultable | Simulador con marcas de tiempo + consulta periódica a la API; percentiles 50 y 95 | p95 < 60 s |

Métricas de apoyo, ya expuestas en Prometheus: eventos por segundo, decisiones por tipo, grupos
enmascarados y % de viajes rechazados por validación.

## Resultados

### M2 · Utilidad tras la protección (medido el 17/09/2026 con el año 2020 completo)

Carga de los 24 648 499 viajes del dataset completo, con k = 10:

| Nivel | Grupos publicados | Grupos suprimidos | Viajes en grupos publicados |
|---|---|---|---|
| hora y zona | 287 016 | 430 113 (60 %) | 22 522 574 (**95,1 %**) |
| día y barrio | 2 253 | 560 (20 %) | 23 682 543 (**100,0 %**) |
| flujos entre barrios por día | 7 926 | 7 448 (48 %) | 23 662 106 (**99,9 %**) |

La conclusión es el argumento central de E3: **el umbral oculta muchos grupos pero muy pocos viajes**.
En el nivel más fino se suprimen 6 de cada 10 grupos, y aun así siguen publicados el 95 % de los
viajes: los grupos ocultos son justo los pequeños, que son los que permitirían identificar a alguien.

Pendiente: repetir con k = 5 y k = 20 para tener la curva privacidad–utilidad.

### Calidad de la ingesta (misma carga)

| | |
|---|---|
| Viajes leídos | 24 648 499 |
| Válidos | 23 684 852 (96,1 %) |
| Rechazados | 963 647 (3,9 %) |
| Motivos | falta un campo obligatorio 809 568 · importe negativo 92 835 · duración excesiva 45 704 · duración no positiva 37 269 · distancia fuera de rango 2 567 · fecha fuera de 2020 280 |
| Tiempo de la carga | **2 min** (Spark en modo cluster, 6 núcleos, 2 workers) |
| Tamaño de los agregados en MongoDB | 214 MB |

### M1 · Tasa de fuga de privacidad

<!-- Sección del bloque «privacidad» (tareas T02 y T03-M1). La parte del chatbot la aporta el bloque
     «chatbot» (T05). No editar desde otros bloques para evitar conflictos al fusionar. -->

_Pendiente de medir._

### M2 · Curva privacidad-utilidad (k = 5, 10, 20, 50)

<!-- Sección del bloque «privacidad» (tarea T02). -->

_Pendiente de medir._

### M3 · Latencia de publicación en tiempo real

<!-- Sección del bloque «observabilidad» (tareas T04, T07 y T03-M3). No editar desde otros bloques. -->

Medida el 21/09/2026 con `make latencia` (`scripts/medir_latencia_tiempo_real.py`), con un único trabajo
`pids-tiempo-real` en marcha. Cada medida envía por `POST /viajes` un lote de 15 viajes válidos a una combinación
hora-zona nueva y consulta `POST /consultas` (fuente `tiempo_real`, nivel `hora_zona`) cada segundo hasta que
aparece ese grupo con sus 15 viajes. El reloj va desde antes del envío hasta la respuesta que lo confirma.

| Serie | Cómo llegan los lotes | Medidas | p50 | p95 | Máximo | Mínimo |
|---|---|---|---|---|---|---|
| 1 | Justo después de publicarse el anterior (31/12/2020 de 0:00 a 19:00, zona 265) | 20/20 | 29,1 s | 33,3 s | 37,2 s | 9,1 s |
| 2 | Con una espera aleatoria de 0 a 30 s: caen en cualquier punto del ciclo (31/12/2020 22:00, zonas 246-265) | 20/20 | 27,6 s | 35,4 s | 40,2 s | 11,1 s |

**Objetivo cumplido: p95 < 60 s** en las dos series, sin ningún lote perdido ni fuera de tiempo.

**Qué pesa en la latencia.** Según el registro de progreso del propio trabajo de streaming:

- **La espera al trigger de 30 s**: en media 15 s, cerca del 60 % de los 25,6 s de media de la serie 2.
- **El micro-lote**: los tres niveles (hora-zona, día-barrio y flujos) se lanzan a la vez en cada trigger y
  compiten por los 2 núcleos de su único ejecutor, así que cada uno tarda de 5 a 15 s aunque solo traiga
  15 viajes (casi todo es `addBatch`: estado de la agregación y escritura en MongoDB). El de hora-zona acaba antes
  o después según el turno que le toque.
- El archivo en la zona restringida (trigger de 10 s, unos 2,5 s por micro-lote) va en paralelo y no retrasa la
  publicación, pero ocupa núcleos del mismo trabajo.

Para bajarla (cambios en Spark, no hechos): un trigger de 10 s dejaría la espera media en 5 s; más núcleos para el
trabajo (con `PIDS_CORES=4` cabrían dos ejecutores de 2 núcleos, frente al único de ahora con `cores.max=3`), o
calcular los tres niveles en una sola consulta que escriba las tres colecciones, quitaría la competencia entre
ellos.

Los viajes sintéticos llevan lotes `latencia-...` y se quedan en el archivo restringido y en
`publico.tr_viajes_hora_zona`. Al ser de finales de 2020 adelantan la *watermark* del streaming: mientras el
trabajo conserve ese estado, los viajes anteriores (como la muestra del 1 de enero) se archivan pero ya no se
agregan (ver `parte2_plataforma/README.md`).
