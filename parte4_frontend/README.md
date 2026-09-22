# Parte 4 · Portal web

Portal corporativo de la plataforma: una sola aplicación web que reúne lo que antes estaba repartido entre Chainlit,
Grafana, Airflow y los `/docs` de las APIs. Está pensado para la demo y para el uso diario del equipo de la empresa
de taxis, y respeta E3 igual que el resto: **solo enseña agregados ya protegidos por la API de acceso** y las
decisiones de la auditoría (que no contienen viajes).

| Sección | Ruta | Qué hace |
|---|---|---|
| Panel | `/` | Viajes del último día publicado (total y por barrio, histórico y tiempo real), decisiones de las últimas 24 h, frescura del *streaming* con semáforo, estado de los servicios y accesos directos |
| Explorador | `/explorador` | Consultas por nivel (hora-zona, día-barrio, flujos), fechas, zona con buscador, barrios y métricas → tabla ordenable, gráfico o matriz de flujos; los grupos `<10` van en violeta y **nunca se suman**; un rechazo muestra los motivos y un botón para lanzar la alternativa |
| Asistente | `/asistente` | Chat con el agente (motor Ollama local o RAG con Helmcode), pasos de las herramientas en directo, fuentes, tokens y botón de alternativa tras un rechazo |
| Tiempo real | `/tiempo-real` | Frescura, viajes por hora de las últimas 6/12/24 h con datos y la última hora por zona; se refresca cada 30 s |
| Privacidad | `/privacidad` | Reglas E3 leídas del catálogo, auditoría de decisiones (por resultado, cliente y motivo, con filtros) y cargas históricas |
| Operaciones | `/operaciones` | Lanzar una carga histórica en Airflow (mes o muestra) y ver sus ejecuciones; iniciar y parar el simulador de tiempo real |
| Documentación | `/documentacion` | Arquitectura, cómo se protege cada respuesta, enlaces a los servicios y equipo |

## Arquitectura

```
navegador ──► frontend (un contenedor, 8020) ─┬─ BFF FastAPI (bff/) ── /api/* ──► API de acceso (clave del cliente `frontend`)
                                              │     guarda las claves, sesión por cookie firmada      API de captura (simulador)
                                              │     ejecuta el agente del chat en el proceso          Prometheus · Airflow · MongoDB (pids_auditor)
                                              └─ SPA React (web/) construida y servida por el propio FastAPI
```

- **El navegador nunca ve una clave**: el BFF guarda las de la API de acceso, la de captura, las de Airflow y la de
  MongoDB, y el usuario entra con una contraseña única del portal (`FRONTEND_CLAVE`) que da una cookie `HttpOnly`
  firmada con HMAC (12 h). El BFF aparece en la auditoría como el cliente `frontend`.
- **Todas las cifras pasan por `POST /consultas` de la API de acceso**, con su filtro de privacidad: el BFF no lee
  `publico` en MongoDB. El panel y el tiempo real se calculan con consultas normales que solo suman los grupos
  visibles; los enmascarados se cuentan aparte.
- El contrato entre el BFF y la SPA (formas JSON, códigos, variables de entorno, sistema de diseño) está en
  [`CONTRATOS.md`](CONTRATOS.md).

## Puesta en marcha

```bash
make entorno-completar            # si el .env es anterior a la parte 4: le añade las variables de abajo
docker compose up -d --no-deps acceso-a acceso-b   # para que la API de acceso conozca la clave del cliente `frontend`
make frontend                     # construye la imagen (node → python) y levanta el portal en http://localhost:8020
```

La contraseña del portal es `FRONTEND_CLAVE` en `.env`. Variables nuevas: `ACCESO_CLAVE_FRONTEND` (clave del cliente
`frontend` en la API de acceso; hay que recrear `acceso` para que la conozca), `FRONTEND_CLAVE`, `FRONTEND_SECRETO` y
`PUERTO_FRONTEND` (8020). Los servicios opcionales (Prometheus, Airflow, Ollama, MongoDB) pueden no estar levantados: el
portal lo indica como «no disponible» sin romperse.

En desarrollo, el BFF corre en el host leyendo `.env` (deriva las URL de los puertos publicados en 127.0.0.1) y la SPA con
Vite, que reenvía `/api` al BFF:

```bash
make frontend-dev                                 # BFF con recarga en http://localhost:8020
cd parte4_frontend/web && npm ci && npm run dev   # SPA en http://localhost:5173
```

**Modo demostración** (la versión pública en Vercel): la misma SPA sin BFF, con datos grabados de la plataforma. Se
construye con `vite.demo.config.ts` y se prueba en http://127.0.0.1:4190; todo está en
[`demo/README.md`](demo/README.md).

## Tests

```bash
make test-frontend                                # pytest del BFF + eslint y vitest de la SPA
uv run pytest -q tests/test_frontend_bff_*.py     # 89 tests: base, plataforma y chat (sin red)
cd parte4_frontend/web && npm test -- --run       # 98 tests con Testing Library y una API simulada
```

Ninguno necesita servicios levantados: la API de acceso falsa de los tests aplica el filtro de privacidad real
(`parte2_plataforma.comun.privacidad`), así que los 403 y los `<10` son los de verdad.

## Estructura

```
parte4_frontend/
├── CONTRATOS.md          contrato BFF ↔ SPA y reparto del trabajo en paralelo
├── bff/
│   ├── app.py            crea la aplicación: routers públicos (salud, sesión) y protegidos, estáticos de la SPA
│   ├── configuracion.py  variables de entorno; en el host lee .env y deriva las URL de los puertos publicados
│   ├── seguridad.py      cookie de sesión firmada y dependencias (configuración, cliente HTTP compartido)
│   ├── estaticos.py      sirve web/dist con fallback a index.html
│   ├── rutas/            sesion · salud · catalogo · consultas · panel · tiempo_real · auditoria · operaciones · chat
│   ├── servicios/        acceso · prometheus · auditoria · airflow · simulacion · chat
│   └── Dockerfile        multi-stage: node:22 construye la SPA; python:3.12 instala el BFF (grupos frontend y chatbot)
└── web/                  Vite + React 19 + TypeScript + Tailwind 4 + shadcn/ui
    └── src/
        ├── api/          cliente tipado (cliente.ts, tipos.ts) y hooks de TanStack Query por sección
        ├── componentes/  shell (barra, cabecera, estados), ui (shadcn), datos (tablas, formato), graficos (Recharts), chat
        ├── paginas/      una carpeta por sección
        └── estilos/      tema corporativo (marino, amarillo taxi, violeta para «enmascarado»)
```

## API del BFF

Todo bajo `/api`, JSON, errores como `{"detail": "…"}`; salvo `/api/salud` y `/api/sesion`, exige la cookie de sesión.
Documentación interactiva en `http://localhost:8020/api/docs`.

| Ruta | Qué devuelve |
|---|---|
| `POST/GET/DELETE /api/sesion` | Entrar con `{"clave"}`, comprobar y salir |
| `GET /api/catalogo` · `GET /api/zonas?texto=` | El catálogo y las zonas de la API de acceso (caché de 10 min) |
| `POST /api/consultas` | La misma respuesta y el mismo código que `POST /consultas` de la API de acceso (200, 403 con alternativa, 422) |
| `GET /api/panel` · `GET /api/tiempo-real?horas=` | Agregados del último día y de las últimas horas (solo grupos visibles), frescura, estado de servicios |
| `GET /api/auditoria/{resumen,decisiones,cargas}` | Lectura de `auditoria` con `pids_auditor` |
| `GET/POST /api/operaciones/airflow/{ejecuciones,cargas}` | Ejecuciones del DAG `pids_carga_historica` y lanzamiento de una carga |
| `GET/POST/DELETE /api/operaciones/simulacion` (+ `/ficheros`) | Simulador integrado sobre `data/muestra` |
| `GET /api/chat/motores` · `POST /api/chat/sesiones` · `POST …/{id}/mensajes` · `POST …/{id}/alternativa` | Chat con eventos SSE `paso`, `respuesta` y `error` |

## Decisiones y límites

- **Un solo contenedor** con FastAPI sirviendo la SPA: menos piezas que nginx + BFF, suficiente para una aplicación
  interna en `127.0.0.1`.
- El BFF está en la red `datos` **solo** para leer la auditoría con `pids_auditor` (rol de solo lectura sobre
  `auditoria`); las cifras publicadas las pide a la API de acceso como cualquier otro cliente.
- El motor `rag` del asistente es el mismo agente del chatbot RAG (`parte3_chatbot_rag/fabrica.py`), ejecutado dentro
  del BFF con las claves del portal; necesita `LLM_API_KEY` en `.env`, Qdrant levantado e indexado (`make rag-indexar`).
  Si la imagen se construye sin el grupo `rag` (`GRUPOS="frontend chatbot"`), el motor aparece como «no disponible».
- El simulador integrado solo admite los ficheros de `data/muestra` (la muestra es del 1 de enero de 2020; si el
  trabajo de tiempo real ya ha visto días posteriores, los descarta por la *watermark*: ver `parte2_plataforma/README.md`).
- Cachés en memoria del BFF (catálogo, meses del panel, tiempo real) para que el refresco automático del portal no
  multiplique las entradas de la auditoría; lo cacheado ya salió filtrado por la API.
