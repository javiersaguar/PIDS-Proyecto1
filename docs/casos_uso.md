# Casos de uso del chatbot

Todos acceden a los datos procesados de la parte 2 a través de la API de acceso.

| # | Caso de uso | Ejemplo | Nivel | Qué demuestra |
|---|---|---|---|---|
| CU1 | Demanda por zona y hora | «¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?» | hora_zona | Búsqueda de zona + consulta agregada |
| CU2 | Comparativa entre barrios | «¿Qué barrio tuvo más viajes el 3 de marzo?» | dia_barrio | Agregado por barrio |
| CU3 | Importes y propinas | «Propina media en Manhattan la primera semana de febrero» | dia_barrio | Métricas protegidas y redondeadas |
| CU4 | Flujos entre barrios | «¿Cuántos viajes hubo de Queens a Manhattan el 10 de enero?» | od_dia_barrio | Destino solo a nivel de barrio y día |
| CU5 | Petición individual (rechazo) | «Dame el viaje de las 3:12 desde Times Square» | — | Rechazo sin pasar por el LLM + alternativa con botón |
| CU6 | Grupos pequeños (enmascarado) | «Viajes por hora desde Staten Island el 1 de enero» | hora_zona | Grupos `<10` sin cifras y explicación |
| CU7 | Tiempo real | «¿Cuántos viajes llevamos en la última hora simulada?» | hora_zona (tiempo_real) | Datos en streaming con la misma protección |
| CU8 | Confirmación por gestos (integración) | El bot propone una alternativa y el usuario hace 👍 | — | Parte 1 → parte 3 |

## Diálogo de ejemplo (CU5)

> **Usuario:** Dame el viaje de las 3:12 desde Times Square
>
> **Bot:** 🔒 Consulta rechazada por privacidad: petición de datos individuales. La plataforma solo
> publica agregados de al menos 10 viajes. Puedo decirte cuántos viajes salieron de Times Square entre
> las 3:00 y las 4:00. [✅ Consultar la alternativa] [✖ Cancelar]
