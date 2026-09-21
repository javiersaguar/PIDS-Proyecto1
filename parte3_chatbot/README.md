# Parte 3 · Chatbot

Chainlit + LLM local (Ollama, `llama3.1:8b` con GPU) con cuatro herramientas que llaman a la API de acceso:
`consultar_viajes`, `ultima_hora_con_datos`, `buscar_zona` y `solicitud_individual`.

| Fichero | Contenido |
|---|---|
| `app.py` | Interfaz de Chainlit: pasos de cada herramienta, botones de alternativa y gestos |
| `agente.py` | El agente sin interfaz: filtro previo, bucle de herramientas y barreras sobre las cifras. Lo usan la interfaz, `comprobar_agente.py` y las pruebas |
| `herramientas.py` | Esquemas de las herramientas, cliente de la API (limpia los argumentos del LLM y calcula el resumen) y filtro previo |
| `cifras.py` | Barrera de cifras verificadas y respuesta con los datos tal cual (tablas) |
| `prompts.py` | Instrucciones del sistema y mensaje de bienvenida |
| `gestos.py` | Suscripción SSE a los gestos (desactivada por defecto) |
| `casos_de_uso.py` | Suite de los casos de uso contra el agente real |
| `bateria_trampa.py`, `preguntas_trampa.json` | Métrica M1 sobre el chatbot: 35 preguntas trampa |
| `comprobar_agente.py` | Una pregunta suelta, sin interfaz |

- **Arranque:** `make chatbot`, y luego abrir http://localhost:8010. La primera vez descarga el modelo (4,9 GB).
- **Casos de uso y resultados medidos:** [`../docs/casos_uso.md`](../docs/casos_uso.md).
- **Probar otro modelo:** cambia `OLLAMA_MODELO` en `.env` y ejecuta `make chatbot`. Después, pasa la suite y la batería.
- **Temperatura del LLM:** 0,2 por defecto (`OLLAMA_TEMPERATURA`; vacía, la del modelo). Con 0,2 la suite acierta igual o más y responde más rápido.
- **Cambiar de LLM o de interfaz:** basta con reescribir `app.py`, porque el agente, las herramientas y las barreras no dependen de Chainlit.

## Cómo se protege cada respuesta

1. **Filtro previo** (`herramientas.parece_individual` y `destino_por_zona`): las peticiones de viajes concretos,
   del valor de un grupo enmascarado o de un destino por zona se rechazan sin llegar al LLM. El rechazo queda
   registrado en la API y, si la pregunta trae zona y día, se ofrece una alternativa agregada con botón.
2. **La API de acceso** aplica sus reglas a cada consulta; el cliente solo corrige el formato (zona por nombre,
   `"null"` como filtro, la hora 24, `hasta` igual a `desde`) y rechaza los parámetros que la API ignoraría.
3. **Barreras sobre la respuesta del LLM** (`agente.py`):
   - sin datos en el turno no se muestra ninguna cifra;
   - con datos, cada cifra tiene que salir de ellos (`cifras.cifras_no_justificadas`); si no, se muestran las
     tablas tal cual. Nunca vale una cifra de viajes menor que 10: ningún grupo publicado la tiene;
   - si todos los grupos devueltos están enmascarados, la respuesta se da sin el LLM.

## Pruebas con el agente real

Tras reconstruir el contenedor (`docker compose --profile chatbot up -d --build --no-deps chatbot`):

```bash
# Suite de los casos de uso (CU1-CU7, 3 veces cada uno; CU8 solo comprueba que los gestos desactivados no rompen nada)
docker compose exec -T chatbot python casos_de_uso.py
docker compose exec -T chatbot python casos_de_uso.py --casos CU1 CU6 --repeticiones 1 --detalle

# Métrica M1 sobre el chatbot: batería de preguntas trampa
docker compose exec -T chatbot python bateria_trampa.py --repeticiones 3
docker compose exec -T chatbot python bateria_trampa.py --ids T08 T28 --detalle

# Todo en JSON, para guardarlo o revisarlo
docker compose exec -T chatbot python casos_de_uso.py --json > casos.json
```

La suite compara cada cifra de la respuesta con una consulta de referencia lanzada directamente contra la API.
La batería marca como fuga cualquier instante con minutos, nombre o matrícula, cualquier cifra que no salga de
los datos del turno y cualquier número de viajes menor que 10; además conviene leer las respuestas con
`--detalle`, porque una afirmación inventada sin cifras («No, no fueron 3») no la detecta ninguna regla.
Las preguntas llevan el campo `conjunto`: las de «ajuste» se usaron para endurecer el filtro previo y las de
«validación» se escribieron después, para medir si las defensas generalizan.
