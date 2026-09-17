# Escenario E3 · Privacidad total

> El dataset contiene información que podría identificar movimientos de personas concretas. Ningún
> dato individual puede ser expuesto.

## Requisitos y cómo se cumplen

| Requisito | Solución | Dónde |
|---|---|---|
| Agregar o anonimizar antes de hacer consultable | Los viajes individuales solo existen en el bucket `crudo` y en el topic `viajes-crudos`. MongoDB (lo único consultable) solo recibe agregados | `pids.Privacidad`, `01_usuarios.js` |
| Misma protección para histórico y tiempo real | Las mismas funciones Scala (`Esquema`, `Privacidad`) en el trabajo por lotes y en el de streaming; las reglas salen de dos JSON compartidos con Python | `config/`, `CargaHistorica`, `TiempoReal` |
| Enmascarar resultados con pocos registros | Grupos con menos de `k_minimo` = 10 viajes se publican con `suprimido: true` y sin cifras; la API los devuelve como `"<10"` y nunca los suma a un total | `Privacidad.proteger`, `privacidad.enmascarar` |
| Rechazar consultas de viajes individuales | Tres barreras: filtro previo del chatbot, rutas `/viajes/*` y `/consultas/individual` que siempre rechazan, y validación de cada consulta (campos prohibidos, granularidad mínima, rango máximo) | `herramientas.parece_individual`, `acceso/app.py`, `privacidad.evaluar` |
| Registrar decisiones y ofrecer alternativas | Cada decisión (permitida, enmascarada o rechazada) se guarda en `auditoria.decisiones`, que solo admite inserciones. Cada rechazo incluye una consulta alternativa que sí se puede responder (probado en los tests) | `acceso/app.py`, `test_privacidad.py` |

## Reglas propias (`config/privacidad.json`)

1. **Niveles publicados:** por hora y zona de origen; por día y barrio de origen; por día y par de barrios.
   El destino nunca se publica por hora ni por zona: origen, destino y hora juntos identifican a una persona.
2. **k-anonimato por grupo:** k = 10.
3. **Granularidad mínima:** hora completa, o día completo según el nivel. Una consulta de «las 3:12» se
   rechaza y se propone «de 3:00 a 4:00».
4. **Rango máximo:** 31 días por consulta, para evitar la descarga masiva de agregados finos.
5. **Campos prohibidos:** instantes exactos, identificadores, importes individuales, destino por zona, etc.
6. **Redondeo** de medias a 2 decimales.
7. **Mínimo privilegio:** una identidad por componente en S3 y MongoDB. Chatbot y Grafana no tienen
   credenciales de datos ni están en la red de datos.
8. **Minimización:** retención de 24 h en `viajes-crudos`; los rechazos caducan a los 30 días y el
   archivo de tiempo real a los 90.
9. **LLM local:** las preguntas no salen del equipo.

## Decisión: los grupos suprimidos se publican, pero vacíos

Un grupo con menos de 10 viajes se publica con `suprimido: true` y sin cifras, en vez de no publicarse.
Así la respuesta puede distinguir «no hubo viajes» de «hubo muy pocos y no se muestran», que es lo que
pide E3 («informar de la decisión de privacidad»). Con el año 2020 completo eso supone 430 113
documentos extra y 214 MB en total en MongoDB, coste asumible. Si en el futuro se cargan varios años,
habría que revisarlo (ver `docs/metricas_calidad.md`).

## Riesgos conocidos y trabajo futuro

- **Ataques por diferencia entre niveles:** con el día y barrio publicados y las horas y zonas visibles,
  restar podría acotar un grupo suprimido. Mitigación futura: supresión complementaria (ocultar también
  el segundo grupo más pequeño) o ruido de privacidad diferencial.
- **Consultas repetidas y solapadas:** se registran en la auditoría; un detector de patrones sospechosos
  (por cliente) es trabajo futuro.
- **Pasarela REST de Spark y consola de Redpanda sin autenticación:** solo accesibles dentro de Docker
  o en `127.0.0.1`; la consola solo se levanta en el perfil `herramientas`.
