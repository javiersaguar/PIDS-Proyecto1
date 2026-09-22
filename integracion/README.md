# Integración gestos ↔ plataforma ↔ chatbots

Es la caja «Integración» de la diapositiva 5: los gestos de la parte 1 entran en la plataforma como una fuente de
datos más, y los chatbots de la parte 3 reaccionan a ellos. Hay dos formas de hacer el gesto, y las dos acaban en
el mismo sitio:

| Dónde se reconoce | Con qué | Cuándo usarla |
|---|---|---|
| **El navegador**, en el portal (botón «Gestos» de TAXI AI) | MediaPipe para web (los 21 puntos de la mano) y **el MLP de la parte 1** exportado a JSON (`parte1_gestos/entrenamiento/exportar_web.py`) | En la demo y en la web pública de Vercel: no hace falta Windows ni Python, basta una cámara |
| **La demo de Windows** (`parte1_gestos/demo/src/demo-gestures-PIDS.py`) | El pipeline de la parte 1 en Python (Keras) | Para enseñar la parte 1 tal cual, con su ventana y los comandos del tanque |

```mermaid
sequenceDiagram
    participant N as Navegador (portal)
    participant W as Demo de Windows
    participant B as BFF del portal
    participant C as API de captura
    participant R as Redpanda (topic gestos)
    participant T as Chatbots de Chainlit (Ollama y RAG)
    N->>N: cámara → MediaPipe → MLP de la parte 1 → filtro
    N->>N: TAXI AI actúa enseguida
    N->>B: POST /api/gestos {gesto, confianza, dispositivo}
    B->>C: POST /gestos (cliente gestos)
    W->>C: POST /gestos (cliente gestos)
    C->>R: evento
    T->>C: GET /gestos/stream (SSE)
    B->>C: GET /gestos/stream (SSE) → portal: los gestos de Windows también manejan TAXI AI
    C-->>T: event: gesto
```

## Qué hace cada gesto

Una sola tabla, [`config/gestos.json`](../config/gestos.json), para los tres chatbots: los dos de Chainlit la leen
con [`parte3_chatbot/gestos.py`](../parte3_chatbot/gestos.py) y TAXI AI con `parte4_frontend/web/src/gestos/tabla.ts`.

| Gesto | Acción | Chainlit (Ollama y RAG) | TAXI AI (portal) |
|---|---|---|---|
| 👍 `thumbsup` | Confirmar | Ejecuta la alternativa agregada que propuso el rechazo | Igual |
| ✋ `paper` | Parar | Descarta la alternativa | Calla la lectura; si no, descarta la alternativa; si no, corta la respuesta |
| ✌️ `scissors` | Otra pregunta | Hace la siguiente pregunta de ejemplo | Igual |
| 👌 `ok` | Leer en voz alta | — | Lee la última respuesta (síntesis de voz del navegador) |
| 🤘 `rockandroll` | Abrir TAXI AI | — | Abre el panel desde cualquier página |
| ✊ `rock` | Cerrar TAXI AI | — | Cierra el panel; la conversación sigue |

Por qué estas: **confirmar y cancelar** son el momento de E3 en el que la persona decide (acepta o no la
alternativa agregada que le ofrece el filtro de privacidad); **otra pregunta** permite recorrer los casos de uso sin
teclado; **leer en voz alta** es para usar el asistente sin mirar la pantalla (un operador, una sala de control), y
**abrir y cerrar** manejan el portal con la mano. Las preguntas de ✌️ son las de `preguntas` en la misma tabla: las
tres de ejemplo, un flujo entre barrios y, la última, una petición individual, para que 👍 confirme su alternativa.
Todas están grabadas en la demostración pública, así que ✌️ también funciona en Vercel sin el equipo.

## Privacidad (E3)

- **Qué sale de la cámara:** solo la etiqueta del gesto y la confianza, nunca la imagen ni los puntos de la mano. En
  el navegador la imagen se procesa en el propio navegador (WebAssembly) y no se envía a nadie.
- **Qué se descarga:** al activar los gestos, el navegador baja el motor de MediaPipe (jsDelivr) y su modelo de la
  mano (Google), con la versión fija, y el MLP de la parte 1 (unos 50 KiB, del propio portal). Son ficheros de código
  y pesos: no llevan datos de nadie.
- **Anti-rebote:** un gesto solo cuenta si se mantiene cuatro predicciones seguidas (una cada 0,25 s, como la demo de
  Windows) con confianza de al menos 0,85, y el mismo no se repite en 3 s. Es la misma lógica en
  `cliente_gestos.py` y en `web/src/gestos/filtro.ts`.
- **Por qué HTTP y no Kafka desde Windows:** el cliente nativo de Kafka carga una DLL que Smart App Control puede
  bloquear; `cliente_gestos.py` solo usa la biblioteca estándar.

## Cómo probarlo

**En el portal (la forma más sencilla):** http://localhost:8020 → «TAXI AI» → «Gestos» y permitir la cámara. La
tarjeta enseña el vídeo en espejo con los puntos de la mano, el gesto que ve el modelo y una barra que se llena al
sostenerlo. Funciona igual en https://happytaxi-rust.vercel.app: en vivo (con el túnel) los gestos entran además en
la plataforma; en la demostración se quedan en el navegador y TAXI AI contesta con las conversaciones grabadas. La
cámara solo se puede usar en https o en localhost.

**Con la demo de Windows**, con la plataforma levantada en WSL:

1. En `.env`, `GESTOS_ACTIVOS=true` y `make chatbot` / `make chatbot-rag` (recrean los contenedores si cambió el
   entorno). El portal no necesita nada: escucha los gestos de la plataforma siempre que tenga la clave de gestos.
2. En Windows:

```powershell
$env:PIDS_CLAVE_GESTOS = "<CAPTURA_CLAVE_GESTOS del .env>"
python parte1_gestos\demo\src\demo-gestures-PIDS.py
```

3. En un chatbot (Chainlit en :8010 o :8011, o TAXI AI en el portal), una pregunta individual (por ejemplo «Dame el
   viaje de las 3:12 del 15 de enero desde Times Square»). El bot propone la alternativa; 👍 la ejecuta y ✋ la
   cancela. Con el chat abierto, ✌️ hace la siguiente pregunta de ejemplo.

Sin cámara, el mismo POST que haría la demo:

```bash
source .env && python integracion/cliente_gestos.py --clave "$CAPTURA_CLAVE_GESTOS" --gesto scissors
```

El gesto llega a todos los chats abiertos a la vez (cada pestaña de Chainlit y cada portal con sesión): conviene tener
uno solo abierto durante la demo. La pestaña del portal que hizo el gesto no lo repite al recibirlo de vuelta.

## Comprobado

- El MLP en TypeScript da las mismas probabilidades que en Python (a 5 decimales) con 24 imágenes reales del dataset
  (`web/src/gestos/modelo.test.ts`); con numpy, el modelo exportado acierta el 98,4 % de las 2931 imágenes con mano.
- En Chromium, con una cámara simulada a partir de fotos del dataset (solo en local; las fotos no se publican):
  ✌️ reconocido al 99 %, `POST /api/gestos` → cola `gestos` → TAXI AI pregunta y responde.
- Un ✌️ enviado como la demo de Windows: los dos chatbots de Chainlit hacen la pregunta y contestan; en el portal,
  🤘 abre TAXI AI, ✌️ pregunta y ✊ lo cierra.
