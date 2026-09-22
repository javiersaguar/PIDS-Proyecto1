# Lo que queda para que el proyecto funcione entero

Inventario del trabajo que aún no está cerrado. La lista corta del día a día sigue en [`../TAREAS.md`](../TAREAS.md);
esto es el mapa. Hecho de verdad es lo que ya está en [`../BITACORA.md`](../BITACORA.md).

Hoy funciona, en este equipo: la plataforma de la parte 2 (captura, Spark, S3, MongoDB, Airflow, Grafana),
el año 2020 cargado, los dos chatbots consultando la API de acceso, el portal con datos reales en
http://localhost:8020 y los gestos de la parte 1 manejando los tres chatbots (con la demo de Windows o con la cámara
del navegador). Vercel enseña la plataforma en vivo con el túnel encendido, o una demostración grabada.

## Parte 1 · gestos

| Qué falta | Tarea |
|---|---|
| Subir la copia del dataset a un sitio solo del grupo y que otra persona reproduzca el preprocesado | T01 |
| Probar los gestos del portal con la webcam de verdad, en local y en Vercel | T18 |

## Parte 2 · plataforma

| Qué falta | Tarea |
|---|---|
| Supresión complementaria también en el tiempo real (hoy solo en la carga histórica) | idea en TAREAS |
| Un DAG que cargue los 12 meses seguidos, con reintentos | idea |
| Que la carga de la muestra no pise los agregados del año completo | T19 |
| Contadores de la API de captura a 0 al arrancar, para que la alerta de frescura vea el primer lote | idea |
| Bajar la latencia del streaming (M3 está en 35 s) | idea |

La conexión del chatbot con la parte 2 ya está: las herramientas llaman a la API de acceso y no a MongoDB.
Lo que no está es el vídeo de esa conversación dentro de la entrega (T10).

## Parte 3 · chatbots

| Qué falta | Tarea |
|---|---|
| Cuando la barrera de cifras sustituye la respuesta del RAG, enseñar solo las fichas de la pregunta | idea |
| Medir el rerank y reindexar Qdrant desde Airflow tras cada carga | idea |

## Parte 4 · portal

El portal en Docker ya lee datos reales (agregados, auditoría, Airflow, Prometheus). La SPA de desarrollo
(`make frontend-dev`) no llega a Prometheus, Ollama ni Qdrant desde el 22/09: esos servicios ya no se
publican. El camino con datos en vivo es `make frontend`.

| Qué falta | Tarea |
|---|---|
| Usuarios y roles (hoy hay una sola contraseña), exportar CSV, modo oscuro | idea |
| La entrega: vídeo de la plataforma, capturas que falten y presentación | T10 |

## Entrega

T10 junta el vídeo (levantar, cargar, panel, chatbot con un rechazo) y las diapositivas, con el guion de
[`guion_demo.md`](guion_demo.md). El gesto se graba en el propio portal (escena 9); si falla, está
[`capturas/cu8_gesto.mp4`](capturas/cu8_gesto.mp4). El checklist de
[`plan.md`](plan.md) sigue con la casilla de capturas o vídeo de la entrega abierta.
