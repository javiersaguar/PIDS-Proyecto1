# Lo que queda para que el proyecto funcione entero

Inventario del trabajo que aún no está cerrado. La lista corta del día a día sigue en [`../TAREAS.md`](../TAREAS.md);
esto es el mapa. Hecho de verdad es lo que ya está en [`../BITACORA.md`](../BITACORA.md).

Hoy funciona, en este equipo: la plataforma de la parte 2 (captura, Spark, S3, MongoDB, Airflow, Grafana),
el año 2020 cargado, los dos chatbots consultando la API de acceso, y el portal con datos reales en
http://localhost:8020. La demo de Vercel es una foto, no la plataforma en vivo.

## Parte 1 · gestos

| Qué falta | Tarea |
|---|---|
| Subir la copia del dataset a un sitio solo del grupo y que otra persona reproduzca el preprocesado | T01 |
| Grabar el vídeo en Windows: el bot propone una alternativa, 👍 la ejecuta y ✋ la cancela. El código y el ciclo por la API ya están | T06 |

## Parte 2 · plataforma

| Qué falta | Tarea |
|---|---|
| Dejar el tiempo real presentable: el watermark está en diciembre de 2020 y la muestra de enero no se agrega | T11 |
| La API dice `"<10"` también de grupos ocultos por supresión complementaria, que pueden tener más viajes | T12 |
| Supresión complementaria también en el tiempo real (hoy solo en la carga histórica) | idea en TAREAS |
| Un DAG que cargue los 12 meses seguidos, con reintentos | idea |
| Contadores de la API de captura a 0 al arrancar, para que la alerta de frescura vea el primer lote | idea |
| Bajar la latencia del streaming (M3 está en 35 s) | idea |

La conexión del chatbot con la parte 2 ya está: las herramientas llaman a la API de acceso y no a MongoDB.
Lo que no está es el vídeo de esa conversación dentro de la entrega (T10) y el botón del portal (T16).

## Parte 3 · chatbots

| Qué falta | Tarea |
|---|---|
| El grupo decide si el LLM externo se queda, se limita a la demo o se retira | T13 |
| Cuando la barrera de cifras sustituye la respuesta del RAG, enseñar solo las fichas de la pregunta | idea |
| Medir el rerank y reindexar Qdrant desde Airflow tras cada carga | idea |
| El gesto 👍/✋ dentro del vídeo, no solo por la API | T06 |

## Parte 4 · portal

El portal en Docker ya lee datos reales (agregados, auditoría, Airflow, Prometheus). La SPA de desarrollo
(`make frontend-dev`) no llega a Prometheus, Ollama ni Qdrant desde el 22/09: esos servicios ya no se
publican. El camino con datos en vivo es `make frontend`.

| Qué falta | Tarea |
|---|---|
| Animar gráficas y el grafo del pipeline cuando entran datos o se lanza un DAG | T15 |
| Sacar el asistente del menú izquierdo y abrirlo con un botón «TAXI AI» abajo a la derecha | T16 |
| Usuarios y roles (hoy hay una sola contraseña), exportar CSV, modo oscuro | idea |
| La entrega: vídeo de la plataforma, capturas que falten y presentación | T10 |

## Entrega

T10 junta el vídeo (levantar, cargar, panel, chatbot con un rechazo y, si da tiempo, el gesto) y las
diapositivas. El checklist de [`plan.md`](plan.md) sigue con la casilla de capturas o vídeo abierta.
