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

### M1 y M3

_Pendientes: ver la tarea T03 en [`../TAREAS.md`](../TAREAS.md)._
