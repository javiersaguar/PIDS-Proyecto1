# Escenario E3 · Privacidad total

> El dataset contiene información que podría identificar movimientos de personas concretas. Ningún
> dato individual puede ser expuesto.

## Requisitos y cómo se cumplen

| Requisito | Solución | Dónde |
|---|---|---|
| Agregar o anonimizar antes de hacer consultable | Los viajes individuales solo existen en el bucket `crudo` y en el topic `viajes-crudos`. MongoDB (lo único consultable) solo recibe agregados | `pids.Privacidad`, `01_usuarios.js` |
| Misma protección para histórico y tiempo real | Las mismas funciones Scala (`Esquema`, `Privacidad`) en el trabajo por lotes y en el de streaming; las reglas salen de dos JSON compartidos con Python. Excepción: la supresión complementaria solo se aplica en lotes (ver «Riesgos conocidos») | `config/`, `CargaHistorica`, `TiempoReal` |
| Enmascarar resultados con pocos registros | Grupos con menos de `k_minimo` = 10 viajes, y los complementarios que impedirían deducirlos restando, se publican con `suprimido: true` y sin cifras. La API los devuelve todos como `"oculto"` (no se puede distinguir cuáles son complementarios: esa marca no se publica) y nunca los suma a un total | `Privacidad.proteger`, `Privacidad.suprimirComplementariosTodos`, `privacidad.enmascarar` |
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
9. **LLM local o proveedor en la UE sin retención.** Con el chatbot de Ollama las preguntas no salen del equipo.
   El chatbot RAG (`parte3_chatbot_rag/`) envía al proveedor Helmcode (infraestructura en la UE, sin registro de
   prompts) la pregunta, el historial de la sesión, el contexto recuperado y los agregados **ya protegidos** que
   devuelve la API de acceso; nunca datos individuales, porque no los tiene: no está en la red de datos ni tiene
   credenciales. Una lista blanca en `llm.py` veta los modelos que el proveedor revende fuera de la UE, y una
   guardia de salida (`salida.py`) revisa cada mensaje antes de enviarlo. Decisión vigente desde el
   22/09/2026 (bitácora): la demo enseña los dos chatbots. Detalle en [`chatbot_rag.md`](chatbot_rag.md).

## Decisión: los grupos suprimidos se publican, pero vacíos

Un grupo suprimido se publica con `suprimido: true` y `n_viajes: "oculto"`, en vez de no publicarse.
Así la respuesta distingue «no hubo viajes» de «el grupo está oculto». No se escribe `"<10"`: con la
supresión complementaria un grupo oculto puede tener 10 o más viajes, y la marca de complementario no
se publica. Es lo que pide E3 («informar de la decisión de privacidad»). Con el año 2020 completo eso supone 430 113
documentos extra y 214 MB en total en MongoDB, coste asumible. Si en el futuro se cargan varios años,
habría que revisarlo (ver `docs/metricas_calidad.md`).

## Ataque por diferencia: medido y mitigado

Ocultar la cifra de un grupo pequeño no basta si esa cifra se puede **deducir restando**. La plataforma
publica los mismos viajes en varios niveles, y los grupos de un día y barrio suman el total de ese día y
barrio, que también se publica:

```
grupo oculto = total del día y barrio − suma de los grupos visibles de ese día y barrio
```

Si en esa partición solo hay un grupo suprimido, su valor sale exacto. También sale si hay varios cuya
suma no deja margen: por ejemplo, once grupos suprimidos que suman 11 tienen, cada uno, exactamente un
viaje.

**El ataque, contra la plataforma real.** `scripts/ataque_diferencia.py` hace de analista externo y
solo usa la API de acceso, con consultas que el filtro permite (por día y barrio, por hora y zona hora a
hora, y flujos por día), sobre los 366 días de 2020: 9 516 consultas en unos 5 minutos, todas registradas
en la auditoría. Prueba dos vectores:

| Vector | Particiones (día, barrio) con suprimidos | Reveladas: valor exacto | Grupos cuyo valor se conoce |
|---|---|---|---|
| grupos hora-zona dentro de su día y barrio | 2 230 | 38 (1,7 %) | 298 |
| flujos que salen de un barrio en un día | 2 123 | 393 (18,5 %) | 481 |
| **Total** | | **431** | **779** |

Los casos hora-zona son sobre todo días de Staten Island (39 de 57 particiones expuestas) en los que
todos los grupos del día están suprimidos: el total del día delata que cada uno tuvo un solo viaje.

**La mitigación: supresión complementaria** (`Privacidad.suprimirComplementariosTodos`, en la carga
histórica):

1. En cada partición (día, barrio) expuesta, es decir, cuando el valor de cada suprimido queda fijado o en
   un rango de uno o dos valores, se suprime también el **grupo visible más pequeño**. Como ese grupo
   tiene 10 o más viajes, la suma oculta deja de poder repartirse.
2. Si la partición expuesta **no tiene ningún grupo visible** (los días de Staten Island), se oculta su
   **total del día y barrio**.
3. La marca que distingue un suprimido complementario de uno pequeño **no se publica**: si el atacante
   supiera cuál es, volvería a despejar el otro.

Cuesta muy poco: 13 grupos hora-zona, 516 flujos y 44 totales día-barrio más, menos del 0,04 % de los
viajes publicados (detalle en [`metricas_calidad.md`](metricas_calidad.md), M2).

**El mismo ataque después de mitigar**, reforzado: si un total día-barrio está oculto pero todos los flujos
que salen de ese barrio son visibles, el atacante lo reconstruye sumándolos y lo usa igual.

| Vector | Reveladas antes | Marcadas como reveladas después | Reveladas de verdad |
|---|---|---|---|
| hora-zona | 38 | 1 | **0** |
| flujos | 393 | 22 | **0** |

Las 23 particiones que el script sigue marcando como reveladas (y las 29 que marca como acotadas a dos
valores) son deducciones erróneas del atacante. Todas tienen 2 o 3 suprimidos que suman 17-18 o 26-27, y
el script concluye «cada uno tiene 8 o 9», pero uno de ellos es un complementario con 10 o más viajes. Por
construcción, cualquier partición expuesta al publicar recibió un complementario, y ninguna de ellas usa
un total reconstruido.

**Atacante que conoce el algoritmo.** Si sabe que el complementario es el menor visible, sabe que vale
entre 10 y el menor de los que siguen visibles. Haciendo la cuenta de forma rigurosa (sin poder descartar
que en la partición no haya complementario), solo consigue acotar **2 particiones de 4 265**, y solo como
conjunto: «uno de estos dos grupos tuvo 8 o 9 viajes», sin saber cuál.

Para repetirlo:

```bash
source .env && uv run python scripts/ataque_diferencia.py --dias 366
```

## Riesgos conocidos y trabajo futuro

- **Tiempo real sin supresión complementaria:** necesita el día completo, y el streaming publica
  micro-lotes con los grupos que cambian (Spark tampoco admite ventanas por partición en streaming). Las
  colecciones `tr_*` siguen expuestas al ataque por diferencia mientras dura el día. Propuesta: aplicarla
  en un trabajo por lotes que cierre cada día cuando el watermark lo deja atrás, y reescriba sus
  documentos.
- **Elección del complementario:** tomar siempre el visible más pequeño da al atacante que conoce el
  algoritmo una cota superior (los 2 casos de arriba). Mejora propuesta: elegirlo al azar entre los
  visibles con una semilla secreta, o exigir que sea al menos el doble de k.
- **Otras combinaciones de niveles:** el ataque cubre las dos relaciones de suma que existen hoy
  (hora-zona y flujos dentro de su día y barrio). Si se publica un nivel nuevo (por ejemplo, un total por
  día para toda la ciudad), habrá que añadir su partición a `Privacidad.particionPadre` y repetir el ataque.
- **Consultas repetidas y solapadas:** se registran en la auditoría; un detector de patrones sospechosos
  (por cliente) es trabajo futuro.
- **Pasarela REST de Spark, su interfaz, Kafka, Prometheus, Ollama, Qdrant y la consola de Redpanda**
  no tienen login y no se publican en el anfitrión. El reparto está en [`seguridad.md`](seguridad.md).
- **LLM externo del chatbot RAG:** la conversación y los agregados protegidos salen del equipo hacia un
  proveedor de la UE que declara no guardar nada. Es una confianza contractual, no técnica: si el grupo no la
  acepta, el chatbot de Ollama da el mismo servicio sin salida de datos. Qué viaja exactamente, en
  [`chatbot_rag.md`](chatbot_rag.md).
