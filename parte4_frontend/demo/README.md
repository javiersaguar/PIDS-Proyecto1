# Portal web · web pública (Vercel): en vivo o demostración

La web pública es la SPA de siempre (`parte4_frontend/web`) construida con `vite.demo.config.ts`. Al abrirse pregunta
por `/api/salud` (`web/src/demo/modo.ts`):

| | En vivo | Demostración |
|---|---|---|
| Cuándo | El equipo tiene el portal y el túnel levantados (`make frontend`, `make tunel`) | El túnel está apagado, o quien entra elige «Ver la demostración» |
| `/api` | Vercel lo reenvía (`vercel.json`) al portal del equipo por un dominio fijo de ngrok | `web/src/demo/`, dentro del navegador, con una instantánea grabada |
| Acceso | La contraseña del portal (`FRONTEND_CLAVE`) | Entra directamente; si se cierra la sesión, cualquier contraseña vale |
| Datos | Los de la plataforma ahora mismo, captura en directo incluida | Agregados reales grabados (ya enmascarados), sin nada del equipo |

El aviso de abajo a la izquierda dice en qué modo se está y deja cambiar: «Ver la demostración» desde el modo en vivo
(para quien no tiene la contraseña) y «Ver en vivo» desde la demostración (si el túnel no responde, lo dice y sigue en
la demostración). La elección se recuerda en esa pestaña.

**El túnel** (`make tunel`, servicio `tunel` del perfil `tunel`) es ngrok con una cuenta gratuita: saca a internet el
portal y nada más, detrás de su contraseña; la conexión la abre ngrok hacia fuera, sin puertos publicados. Hasta que
se pone el dominio en `vercel.json`, la regla de `/api` apuntaba a un nombre `.invalid` (reservado, nunca resuelve),
para que ninguna petición acabara en un dominio de otra persona. El del equipo es
`street-humorous-squeezing.ngrok-free.dev` (el token está solo en `.env`). No hace falta el ngrok de Windows: con el
mismo dominio, solo puede haber un túnel encendido a la vez. Pasos en el README principal («Portal web y web
pública»). La demostración no depende de nada del equipo: con el portátil apagado la web sigue funcionando.

## Qué enseña la demostración

- **Explorador**: el filtro de privacidad de la API portado a TypeScript (`web/src/demo/privacidad.ts`, con las
  reglas de `config/privacidad.json`) decide cada consulta igual que la API: rechazos con sus motivos y su
  alternativa, ventanas alineadas, rango máximo, campos individuales. Las filas son las que ya devolvió la API,
  con los grupos de menos de 10 viajes como `"<10"`. Hay datos de todo 2020 por día y barrio y por flujos entre
  barrios; por hora y zona, el 01/01, 15/01, 03/03 y 15/03 completos y todo el año para JFK (132), LaGuardia (138),
  Times Square (230) y Stapleton (221). Si una consulta pide horas que no están grabadas, la nota de la respuesta
  lo dice.
- **Panel y tiempo real**: el último día publicado (31/12/2020); el tiempo real reproduce el 03/03/2020 y su
  frescura es la mediana medida de la latencia (M3, 27,6 s). El estado de los servicios y las decisiones de las
  últimas 24 h son los del momento de la grabación.
- **Asistente**: reproduce, con sus pasos, conversaciones grabadas del agente de Ollama (las tres preguntas de
  ejemplo, un flujo entre barrios, un grupo enmascarado y cuatro intentos de sacar datos individuales, dos de ellos
  con su alternativa). A cualquier otra pregunta contesta que en la demostración no hay modelo y ofrece las
  grabadas. El motor RAG aparece como no disponible.
- **Privacidad**: las reglas E3, la auditoría (resúmenes y las últimas decisiones de cada tipo) y las cargas.
- **Operaciones**: las últimas ejecuciones de Airflow; lanzar una carga o el simulador contesta que en la
  demostración no se lanzan operaciones.
- **Grafo**: «Capturar datos» anima el camino de la captura con un reloj de 2020 que avanza, pero no envía nada ni
  cambia el tiempo real grabado (lo dice el propio control).
- **Observabilidad**: los ocho cuadros de Grafana con los datos de Prometheus del momento de la grabación
  (`public/demo/observabilidad/`, «Datos grabados el …» en la página). Son métricas de la plataforma: estado de los
  servicios, colas, Spark, tamaños de las colecciones y los totales por barrio que ya publica la API (sin los grupos
  de menos de 10). Se regraban solos con la instantánea completa o con
  `uv run python -m parte4_frontend.demo.instantanea --solo-observabilidad` (portal levantado).

## Ficheros

| Fichero | Qué hace |
|---|---|
| `vercel.json` (raíz) | Instala y construye `parte4_frontend/web` con `vite.demo.config.ts`, publica `dist/` y reenvía `/api` al túnel. Fija el *framework* en Vite: sin él, Vercel ve el `pyproject.toml` de la raíz, cree que es una app FastAPI y falla con «No FastAPI entrypoint found» |
| `web/vite.demo.config.ts` | La configuración de siempre con otro punto de entrada (`src/demo/entrada.ts`) y el puerto 4190 |
| `web/src/demo/entrada.ts` | Decide el modo, instala el sustituto del BFF (demostración) o la cabecera del túnel (en vivo), monta el aviso y carga `src/main.tsx` sin cambios |
| `web/src/demo/modo.ts`, `vivo.ts` | Si contesta el portal por el túnel, y las peticiones en vivo con la cabecera que salta la página de aviso de ngrok |
| `web/src/demo/instalar.ts` | Sustituye `fetch` para `/api/*` (el resto de peticiones salen normalmente); el chat llega como `text/event-stream` con los pasos espaciados |
| `web/src/demo/rutas.ts` | Las rutas del BFF (CONTRATOS.md §5) con las mismas formas y códigos, sobre la instantánea |
| `web/src/demo/privacidad.ts` | `privacidad.evaluar`, la validación de `Consulta`, la proyección y el enmascarado de la API |
| `web/src/demo/datos.ts` | Lee la instantánea a demanda (cada fichero, la primera vez que hace falta) |
| `web/src/demo/privacidad.test.ts` | Compara la demo con 25 respuestas reales de la API (`referencias.json`) y prueba el resto de rutas |
| `web/public/demo/*.json` | La instantánea (unos 4,8 MB; Vercel la sirve comprimida) |
| `demo/instantanea.py` | Graba la instantánea desde la plataforma levantada |

## Comandos

```bash
# Probar la demostración en local (desde parte4_frontend/web)
npx vite build --config vite.demo.config.ts
npx vite preview --config vite.demo.config.ts        # http://127.0.0.1:4190

# Tests (entran en `npm test` con el resto de la SPA)
npx vitest run src/demo

# Regrabar la instantánea (desde la raíz, con la plataforma levantada: acceso, Prometheus, MongoDB, Airflow, Ollama)
uv run python -m parte4_frontend.demo.instantanea
uv run python -m parte4_frontend.demo.instantanea --sin-chat     # sin regrabar el asistente (tarda un par de minutos)
```

El puerto 4190 no coincide con ninguno de la plataforma (8001, 8002, 8010-8012, 8020, 8085, 8090, 3000, 9090…) ni
con el servidor de desarrollo (5173).

`instantanea.py` hace unas 270 consultas normales a la API de acceso con la clave `equipo`, que quedan en la
auditoría como las de cualquier cliente; por eso graba primero el panel y la auditoría. Solo guarda lo que la API
devuelve (agregados ya protegidos), el estado de Prometheus, la auditoría leída con el usuario de solo lectura
`pids_auditor`, las ejecuciones de Airflow y las respuestas del agente; ninguna clave. Antes de subir una
instantánea nueva conviene comprobar que ningún valor de `.env` aparece en `web/public/demo/` (el único que aparece
es el nombre del modelo, `llama3.1:8b`).

**Regrabar la instantánea tras T08.** Prometheus y Ollama ya no se publican en el anfitrión, así que
`instantanea.py` no llega a ellos desde fuera de Docker. Hasta adaptarlo, la instantánea del 21/09 sigue valiendo: el
modo en vivo enseña los datos de hoy.
