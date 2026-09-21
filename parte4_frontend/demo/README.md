# Portal web · modo demostración (Vercel)

El portal tiene dos modos. La SPA (`parte4_frontend/web`) es la misma en los dos; solo cambia quién contesta a
`/api`.

| | Datos reales | Demostración |
|---|---|---|
| Dónde | En el equipo del grupo, con la plataforma levantada | Vercel, público |
| `/api` | El BFF (`parte4_frontend/bff`), que habla con la API de acceso, Prometheus, MongoDB, Airflow y Ollama | `web/src/demo/`, dentro del navegador, con una instantánea grabada |
| Cómo se arranca | Portal en el puerto 8020 (`make frontend`, CONTRATOS.md §8) o `npm run dev` (5173) con el BFF | `vite.demo.config.ts` (puerto 4190 en local); en Vercel, `vercel.json` de la raíz |
| Acceso | Contraseña del portal (`FRONTEND_CLAVE`) | Entra directamente; si se cierra la sesión, cualquier contraseña vale |

Vercel no puede llegar a la plataforma (está en Docker en el equipo del grupo y la API de acceso no se publica en
internet), así que la versión pública no tiene servidor: la SPA de siempre lleva un sustituto del BFF que contesta
con datos grabados de la plataforma de verdad. Nada de la plataforma ni ninguna clave sale del equipo.

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

Un aviso fijo, abajo a la izquierda, recuerda que los datos son grabados y enlaza con este fichero.

## Ficheros

| Fichero | Qué hace |
|---|---|
| `vercel.json` (raíz) | Instala y construye `parte4_frontend/web` con `vite.demo.config.ts` y publica `dist/`. Fija el *framework* en Vite: sin él, Vercel ve el `pyproject.toml` de la raíz, cree que es una app FastAPI y falla con «No FastAPI entrypoint found» |
| `web/vite.demo.config.ts` | La configuración de siempre con otro punto de entrada (`src/demo/entrada.ts`) y el puerto 4190 |
| `web/src/demo/entrada.ts` | Instala el sustituto del BFF y el aviso, y carga `src/main.tsx` sin cambios |
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
