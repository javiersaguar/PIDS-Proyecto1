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

_Pendiente de medir cuando la plataforma esté desplegada._
