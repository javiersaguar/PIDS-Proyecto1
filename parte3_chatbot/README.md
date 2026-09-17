# Parte 3 · Chatbot

Chainlit + LLM local (Ollama, `llama3.1:8b` con GPU) con tres herramientas que llaman a la API de acceso:
`consultar_viajes`, `buscar_zona` y `solicitud_individual`.

| Fichero | Contenido |
|---|---|
| `app.py` | Conversación, bucle de herramientas, botones de alternativa y gestos |
| `herramientas.py` | Esquemas de las herramientas, cliente de la API y filtro previo de peticiones individuales |
| `prompts.py` | Instrucciones del sistema y mensaje de bienvenida |
| `gestos.py` | Suscripción SSE a los gestos (desactivada por defecto) |

- **Arranque:** `make chatbot`, y luego abrir http://localhost:8010. La primera vez descarga el modelo (4,9 GB).
- **Casos de uso:** [`../docs/casos_uso.md`](../docs/casos_uso.md).
- **Probar otro modelo:** cambia `OLLAMA_MODELO` en `.env` y ejecuta `make chatbot`.
- **Cambiar de LLM o de interfaz:** basta con reescribir `app.py`, porque las herramientas y el filtro no dependen de Chainlit ni de Ollama.
