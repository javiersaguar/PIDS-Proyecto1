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

La curva completa, con k = 5, 10, 20 y 50, está más abajo, en «M2 · Curva privacidad-utilidad».

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

**Fugas directas en la API (medido el 21/09/2026):** `scripts/bateria_privacidad.py` lanza 31
peticiones trampa y revisa cada respuesta buscando campos individuales, grupos de menos de 10 viajes con
su cifra visible y métricas de grupos suprimidos.

| Tipo de trampa | Casos | Respuesta | Fugas |
|---|---|---|---|
| Viajes concretos (rutas `/viajes/…`, petición individual) | 4 | 403 rechazada | 0 |
| Instantes exactos y granularidad (minutos, medias horas, ventanas vacías o al revés, tiempo real) | 6 | 403 rechazada | 0 |
| Campos y métricas individuales (recogida, llegada, importe, destino por zona, campos como texto) | 6 | 403 rechazada | 0 |
| Destino a nivel fino y flujos por zona | 2 | 403 rechazada | 0 |
| Rangos enormes, barrios inventados, inyección en el barrio | 3 | 403 rechazada | 0 |
| Operador de MongoDB, nivel inexistente, JSON mal formado | 3 | 422 validación | 0 |
| Sin clave o con clave falsa | 2 | 401 | 0 |
| Consultas legítimas que caen en grupos pequeños (EWR de madrugada, todas las zonas a las 4:00, flujos de Staten Island, un mes entero que se trunca, campo desconocido) | 5 | 200 enmascarada | 0 |
| **Total** | **31** | **31 como se esperaba** | **0 (0,0 %)** |

**Fugas indirectas (combinando consultas legítimas):** es el ataque por diferencia, descrito con cifras
en [`escenario_E3.md`](escenario_E3.md). Antes de la mitigación revelaba el valor exacto de **779 grupos
suprimidos**; después, ninguno.

Cómo repetirlo: `source .env && uv run python scripts/bateria_privacidad.py` (el detalle queda en
`informes/`).

**En el chatbot (medido el 21/09/2026):** `parte3_chatbot/bateria_trampa.py` lanza 35 preguntas trampa
(`parte3_chatbot/preguntas_trampa.json`) contra el agente real: paráfrasis de peticiones individuales, valor de
grupos enmascarados y ataques por diferencia, inyección de instrucciones, inglés, varios mensajes seguidos y
campos prohibidos. Se evalúa lo que ve el usuario (instantes con minutos, nombres o matrículas, cifras que no
salen de los datos del turno y números de viajes menores que 10) y, además, se revisan a mano todas las
respuestas.

| Conjunto | Ejecuciones | Con fuga |
|---|---|---|
| Ajuste (25 preguntas × 3) | 75 | 0 |
| Validación (10 preguntas × 3) | 30 | 0 |
| de ellas, preguntas nunca usadas para ajustar | 21 | 0 |
| **Total** | **105** | **0 (0 %)** |

Una medición intermedia sí tuvo un fallo (1/70): el modelo contestó «No.» a «¿fueron 3 o 4?» sobre un grupo
enmascarado, una afirmación inventada que ninguna regla automática detecta. Se arregló en el filtro previo.
Detalle, evolución y qué defensa paró cada pregunta en [`casos_uso.md`](casos_uso.md).

Cómo repetirlo: `docker compose exec -T chatbot python bateria_trampa.py --repeticiones 3 --detalle`.

**En el chatbot RAG (medido el 21/09/2026):** `make rag-bateria` lanza las mismas 35 preguntas contra el segundo
chatbot (LangChain + Qdrant + `deepseek-v4-flash` en Helmcode), con los mismos detectores y una comprobación más: las
cifras que el chatbot toma de una ficha del índice se verifican contra la API en vivo. Ninguna de las preguntas se
usó para ajustar nada de este chatbot.

| Conjunto | Ejecuciones | Con fuga |
|---|---|---|
| Ajuste (25 preguntas × 3) | 75 | 0 |
| Validación (10 preguntas × 3) | 30 | 0 |
| **Total** | **105** | **0 (0 %)** |

Defensas por turno (132): filtro previo 87, el modelo no da datos 13, barrera de cifras 10, agregados verificados 9,
rechazo de la API 7, todo enmascarado 6. Revisión manual de los 132 turnos sin hallazgos. Hay una fuga que ninguna
regla mide y que aquí sí aplica: **lo que sale hacia el proveedor**. Se controla con la guardia de salida
(`parte3_chatbot_rag/salida.py`) y se documenta en [`chatbot_rag.md`](chatbot_rag.md).

### M2 · Curva privacidad-utilidad (k = 5, 10, 20, 50)

Calculada con el trabajo Spark `pids.AnalisisPrivacidad` sobre los 23 684 852 viajes válidos del año, sin
publicar nada ni cambiar la configuración: para cada umbral k, cuántos grupos se suprimen y qué parte de
los viajes queda en grupos publicados. La fila de k = 10 coincide exactamente con lo que hay publicado.

| k | hora-zona: grupos suprimidos | hora-zona: viajes publicados | flujos: grupos suprimidos | flujos: viajes publicados | día-barrio: grupos suprimidos |
|---|---|---|---|---|---|
| 5 | 48,0 % | 97,5 % | 36,9 % | 100,0 % | 12,0 % |
| **10** | **60,0 %** | **95,1 %** | **48,4 %** | **99,9 %** | **19,9 %** |
| 20 | 71,1 % | 90,4 % | 57,6 % | 99,8 % | 28,3 % |
| 50 | 83,7 % | 78,4 % | 67,3 % | 99,6 % | 32,9 % |

Grupos totales: 717 129 hora-zona, 15 374 de flujos y 2 813 día-barrio.

**Coste de la supresión complementaria** (mitigación del ataque por diferencia), con k = 10:

| Nivel | Suprimidos solo por k | Con la complementaria | Viajes publicados |
|---|---|---|---|
| hora-zona | 430 113 | 430 126 (+13) | 22 522 574 → 22 522 415 (−159) |
| flujos entre barrios | 7 448 | 7 964 (+516) | 23 662 106 → 23 653 221 (−8 885) |
| día-barrio | 560 | 604 (+44) | 23 682 543 → 23 682 022 (−521) |

Proteger contra el ataque cuesta menos del 0,04 % de los viajes publicados.

**Conclusión sobre k.** El nivel más fino es el que decide: pasar de k = 5 a 10 cuesta 2,4 puntos de
viajes publicados (97,5 → 95,1 %) y duplica el tamaño mínimo de un grupo visible; de 10 a 20 cuesta 4,7
puntos más, y de 20 a 50 otros 12. El codo de la curva está entre 10 y 20. **Se mantiene k = 10**: es el
último punto antes de que la pérdida de utilidad se acelere, y con la supresión complementaria ya no se
puede deducir el valor de los grupos ocultos restando. Si el grupo prefiere priorizar la privacidad, k = 20
sigue publicando el 90 % de los viajes.

Cómo repetirlo:
`docker compose exec -T -e PIDS_CORES=6 spark-master /opt/pids/lanzar.sh AnalisisPrivacidad`
(unos 8 minutos; la tabla sale en el log del driver y el JSON en `s3://crudo/informes/curva_privacidad.json`).

### M3 · Latencia de publicación en tiempo real

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
