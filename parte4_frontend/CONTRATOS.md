# Parte 4 · Portal web (frontend) · Contratos

Portal corporativo de la plataforma de datos de la empresa de taxis (PIDS 26/27, escenario **E3: privacidad
total**). Sustituye a las interfaces sueltas (Chainlit, Grafana, Airflow, `/docs` de las APIs) por una sola
aplicación web con diseño profesional que cubre: panel de inicio, explorador de agregados, asistente
conversacional, tiempo real, privacidad y auditoría, operaciones y documentación.

Este fichero es el contrato entre las piezas y entre las personas (o agentes) que las construyen en paralelo.
**Léelo entero antes de tocar nada.** Si algo del contrato no se puede cumplir, no lo cambies en silencio:
dilo en el mensaje final o en la descripción del *pull request*.

## 1. Arquitectura

```
navegador ──HTTP──► frontend (un contenedor, puerto 8020, perfil Compose `frontend`)
                     ├── FastAPI «BFF» (parte4_frontend/bff)  ── /api/*  ──► API de acceso (X-API-Key del BFF)
                     │      guarda todas las claves; el navegador nunca ve ninguna      API de captura (simulador)
                     │      sesión por cookie firmada (contraseña del portal en .env)   Prometheus (estado, frescura)
                     │      ejecuta el agente del chat en el proceso (Ollama y RAG)    Airflow (cargas históricas)
                     │                                                                   MongoDB `auditoria` (pids_auditor, solo lectura)
                     └── SPA React (parte4_frontend/web) servida por el propio FastAPI desde web/dist (fallback a index.html)
```

- **Un solo contenedor** (`parte4_frontend/bff/Dockerfile`, multi-stage: `node:22` construye la SPA, `python:3.12-slim`
  instala el BFF con `uv` y copia `web/dist`). Sin nginx.
- **Redes Compose:** `servicios` (APIs, Prometheus, Airflow, Ollama) y `datos` (solo para leer `auditoria` en MongoDB
  con el usuario `pids_auditor`, que no puede leer ni escribir nada más). El navegador solo llega al 8020.
- **E3:** el portal solo enseña agregados ya protegidos por la API de acceso y las decisiones de la auditoría (que no
  contienen viajes). Ningún endpoint del BFF devuelve viajes individuales ni claves. Todas las consultas pasan por
  `POST /consultas` de la API de acceso, con su filtro de privacidad: el BFF no consulta `publico` en MongoDB.
- **En desarrollo:** el BFF corre en el host (`uv run uvicorn parte4_frontend.bff.app:app --port 8020 --reload`) y la
  SPA con Vite (`npm run dev`, puerto 5173, proxy de `/api` al 8020). El BFF lee `.env` de la raíz del repositorio y
  deriva las URL de los servicios de los puertos publicados (ver §3).

## 2. Propiedad de ficheros (nadie edita lo de otro)

| Agente | Tema | Ficheros que posee |
|---|---|---|
| **F0** | Cimientos | `parte4_frontend/web/*` (configuración: `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`, `index.html`, `eslint.config.js`, `components.json`), `web/src/main.tsx`, `web/src/App.tsx`, `web/src/rutas.tsx`, `web/src/estilos/**`, `web/src/componentes/ui/**` (shadcn), `web/src/componentes/shell/**` (barra lateral, cabecera, pie, guardia de sesión), `web/src/api/cliente.ts`, `web/src/api/tipos.ts`, `web/src/api/sesion.ts`, `web/src/paginas/acceso/**`, los **ficheros de página vacíos** del §6, `parte4_frontend/bff/{__init__,app,configuracion,seguridad,estaticos}.py`, `bff/rutas/{__init__,salud,sesion}.py`, los **routers vacíos** del §5, `bff/servicios/__init__.py`, `bff/Dockerfile`, `pyproject.toml`, `uv.lock`, `docker-compose.yml`, `Makefile`, `.env.example`, `.dockerignore`, `.github/workflows/ci.yml`, `tests/test_frontend_bff_base.py` |
| **F1** | BFF · plataforma | `bff/rutas/{consultas,catalogo,panel,tiempo_real,auditoria,operaciones}.py`, `bff/servicios/{acceso,prometheus,airflow,auditoria,simulacion}.py`, `tests/test_frontend_bff_plataforma.py` |
| **F2** | BFF · chat | `bff/rutas/chat.py`, `bff/servicios/chat.py`, `tests/test_frontend_bff_chat.py` |
| **F3** | Web · datos | `web/src/paginas/{panel,explorador,tiempo-real}/**`, `web/src/api/{panel,consultas,tiempoReal}.ts`, `web/src/componentes/graficos/**`, `web/src/componentes/datos/**`, sus tests `*.test.tsx` junto a cada fichero |
| **F4** | Web · asistente y administración | `web/src/paginas/{asistente,privacidad,operaciones,documentacion}/**`, `web/src/api/{chat,auditoria,operaciones}.ts`, `web/src/componentes/chat/**`, sus tests |
| **F5** (fase final) | Integración y documentación | `parte4_frontend/README.md`, `docs/frontend.md`, `docs/arquitectura.md`, `README.md`, `BITACORA.md`, `TAREAS.md` |

Reglas:

1. **No se toca** `parte2_plataforma/`, `parte3_chatbot/`, `parte3_chatbot_rag/`, `config/`, `scripts/` ni los tests
   existentes. Lo que haga falta de ahí se **importa** (`parte2_plataforma.comun.privacidad`, `parte3_chatbot`) o, si hay
   que cambiarlo, se copia a `parte4_frontend/`.
2. **Dependencias:** F0 instala todas las previstas (§7). F1-F4 **no añaden dependencias** ni tocan `package.json`,
   `package-lock.json`, `pyproject.toml` ni `uv.lock`; si algo falta, se dice en el mensaje final.
3. **Ficheros compartidos** (`rutas.tsx`, `app.py`, `tipos.ts`, `cliente.ts`): solo F0. Por eso F0 deja creados los
   ficheros de página y los routers **vacíos** con los nombres exactos del §5 y §6, y F1-F4 los **rellenan**
   (sobrescribiéndolos). Los tipos TypeScript de las respuestas del BFF están en `web/src/api/tipos.ts` (§5); si F3 o F4
   necesitan un tipo que no está, lo definen en su propio fichero de `web/src/api/`.
4. **Tests sin red:** BFF con `httpx.MockTransport` (como `tests/test_chatbot.py`) y fakes para MongoDB/Airflow/Prometheus;
   web con Vitest + Testing Library y el cliente de la API simulado. `uv run pytest -q` y, en `web/`, `npm run lint`,
   `npm test -- --run` y `npm run build` tienen que pasar antes de dar nada por terminado.
5. **Idioma y estilo:** todo en español (código, textos, comentarios, mensajes de commit). Python tipado con la lógica
   pura separada de la entrada/salida; TypeScript estricto; componentes pequeños. Ningún secreto en el repositorio.
6. **Solo la carpeta principal del repositorio ejecuta `docker compose`.** Para probar contra la plataforma levantada
   (ya está en marcha en este equipo) se usan los puertos publicados en `127.0.0.1` (§3) desde el host.
7. Cada agente termina con un **mensaje final** que incluya: qué ha hecho, cómo comprobarlo (comandos), qué queda
   pendiente y qué necesita de otros ficheros (F5 lo consolidará en la bitácora).

## 3. Configuración (variables de entorno)

En el contenedor las pone Compose; en el host, `bff/configuracion.py` lee `.env` de la raíz (el entorno del proceso
tiene prioridad) y deriva las URL de los puertos publicados, porque los nombres de los contenedores no resuelven fuera
de Docker (misma técnica que `parte3_chatbot_rag/fabrica.py`, rama `rag/4-interfaz`).

| Variable | En Compose | En el host (derivada) | Uso |
|---|---|---|---|
| `PUERTO_FRONTEND` | `8020` (publicado en 127.0.0.1) | — | Puerto del portal |
| `FRONTEND_CLAVE` | de `.env` (aleatoria, `make entorno`) | de `.env` | Contraseña única del portal (formulario de acceso) |
| `FRONTEND_SECRETO` | de `.env` (aleatoria) | de `.env` | Firma HMAC de la cookie de sesión |
| `ACCESO_URL` / `ACCESO_CLAVE` | `http://acceso:8000` / `${ACCESO_CLAVE_FRONTEND}` | `http://127.0.0.1:${PUERTO_ACCESO}` / `ACCESO_CLAVE_FRONTEND` o, si no existe, `ACCESO_CLAVE_EQUIPO` | API de acceso (cliente `frontend` en su auditoría) |
| `CAPTURA_URL` / `CAPTURA_CLAVE` | `http://captura:8000` / `${CAPTURA_CLAVE_SIMULADOR}` | `http://127.0.0.1:${PUERTO_CAPTURA}` / `CAPTURA_CLAVE_SIMULADOR` | Simulador integrado |
| `PROMETHEUS_URL` | `http://prometheus:9090` | `http://127.0.0.1:${PUERTO_PROMETHEUS}` | Estado de servicios, frescura, KPIs y los datos de los cuadros de Observabilidad |
| `GRAFANA_URL` | `http://grafana:3000` | `http://127.0.0.1:${PUERTO_GRAFANA}` | Estado de las alertas en Observabilidad (lectura anónima) |
| `GESTOS_CLAVE` | `${CAPTURA_CLAVE_GESTOS}` | `CAPTURA_CLAVE_GESTOS` | Gestos del navegador hacia la API de captura (cliente `gestos`) y flujo de los de la plataforma |
| `AIRFLOW_URL` / `AIRFLOW_USUARIO` / `AIRFLOW_CLAVE` | `http://airflow-apiserver:8080` / `${AIRFLOW_ADMIN_USER}` / `${AIRFLOW_ADMIN_PASSWORD}` | `http://127.0.0.1:${PUERTO_AIRFLOW}` | Cargas históricas (API REST v2 de Airflow 3: `POST /auth/token` → JWT) |
| `AUDITORIA_MONGO_URI` | `mongodb://pids_auditor:${MONGO_AUDITOR_PASSWORD}@mongo:27017/?authSource=admin` | `mongodb://pids_auditor:…@127.0.0.1:${PUERTO_MONGO}/?authSource=admin` | Lectura de `auditoria.decisiones` y `auditoria.cargas` |
| `OLLAMA_URL` / `OLLAMA_MODELO` | `http://ollama:11434` / `${OLLAMA_MODELO}` | `http://127.0.0.1:${PUERTO_OLLAMA}` | Motor de chat local |
| `ENLACES_*` | `ENLACES_GRAFANA=http://localhost:3000`, `ENLACES_AIRFLOW=http://localhost:8085`, `ENLACES_CHATBOT=http://localhost:8010`, `ENLACES_CHATBOT_RAG=http://localhost:8011`, `ENLACES_API_ACCESO=http://localhost:8002/docs`, `ENLACES_API_CAPTURA=http://localhost:8001/docs`. `ENLACES_SPARK` vacío: la interfaz no se publica | iguales | Enlaces del menú (son URL del navegador del usuario, no del contenedor) |

Nuevas en `.env.example` (F0): `ACCESO_CLAVE_FRONTEND=`, `FRONTEND_CLAVE=`, `FRONTEND_SECRETO=`, `PUERTO_FRONTEND=8020`.
`scripts/generar_env.py` ya rellena con aleatorio cualquier valor vacío. En `docker-compose.yml`, el servicio `acceso`
añade `frontend=${ACCESO_CLAVE_FRONTEND}` a `ACCESO_CLAVES`.

Servicios opcionales (Prometheus, Airflow, Ollama, MongoDB): si no responden, el BFF devuelve `disponible: false` o
`null` en ese campo y el portal lo muestra como «no disponible»; **nunca** un 500. Excepciones acordadas: sin la API
de acceso, `/consultas`, `/catalogo` y `/zonas` responden **503** con `detail` (no hay nada que mostrar), mientras que
`/panel` y `/tiempo-real` responden 200 con `acceso_disponible: false`; Airflow caído → **503** en `/operaciones/airflow/*`
(la SPA muestra su tarjeta de error con «Reintentar»); Airflow que rechaza la petición → 409 o 502 con su detalle.
Cachés en memoria del BFF: catálogo y zonas 10 min; meses de `dia_barrio` 60 s; tiempo real 20 s (para que el refresco
de 30 s del portal no multiplique las entradas de la auditoría; lo cacheado ya salió filtrado por la API).

## 4. Sesión y seguridad del portal

- `POST /api/sesion` `{"clave": "…"}` → `204` y cookie `pids_sesion` (HttpOnly, SameSite=Lax, 12 h) firmada con HMAC-SHA256
  (`FRONTEND_SECRETO`); `401` si la clave no coincide (comparación en tiempo constante, `secrets.compare_digest`).
- `GET /api/sesion` → `{"autenticado": true|false}`. `DELETE /api/sesion` → `204` y borra la cookie.
- Todo `/api/*` excepto `/api/salud` y `/api/sesion` exige la cookie: sin ella, `401 {"detail": "Sesión no iniciada"}`.
  La SPA redirige a `/acceso` al recibir un 401.
- El BFF no registra en los logs ni claves ni el contenido de las conversaciones.
- Las peticiones a la API de acceso llevan la clave del cliente `frontend`; sus decisiones quedan en la auditoría con ese
  nombre, distinguibles de las del chatbot.

## 5. API del BFF (`/api`, JSON, errores como `{"detail": "…"}`)

Tipos en TypeScript (los escribe F0 en `web/src/api/tipos.ts`; F1 y F2 devuelven exactamente estas formas):

```ts
// --- plataforma (F1) ---
export type Nivel = 'hora_zona' | 'dia_barrio' | 'od_dia_barrio';
export type Fuente = 'historico' | 'tiempo_real';
export type Metrica = 'n_viajes' | 'distancia_media' | 'importe_medio' | 'propina_media' | 'pct_pago_tarjeta';

export interface Catalogo {                      // GET /api/catalogo  (proxy de GET /catalogo de la API de acceso)
  k_minimo: number; max_dias_por_consulta: number; metricas: Metrica[];
  niveles: Record<Nivel, { descripcion: string; dimensiones: string[] }>;
  fuentes: Fuente[]; barrios: string[];
}
export interface Zona { _id: number; nombre: string; barrio: string; tipo_servicio?: string }   // GET /api/zonas?texto=

export interface Consulta {                      // POST /api/consultas (cuerpo) — la misma Consulta de la API de acceso
  nivel: Nivel; fuente?: Fuente; desde: string; hasta: string;             // ISO sin zona: 2020-01-15T08:00:00
  metricas?: Metrica[]; zona_origen?: number | null; barrio_origen?: string | null; barrio_destino?: string | null;
}
export interface Fila {                          // una fila de agregados; n_viajes es "oculto" si el grupo está enmascarado
  hora?: string; dia?: string; zona_origen?: number; zona_origen_nombre?: string;
  barrio_origen?: string; barrio_destino?: string; n_viajes: number | string; suprimido: boolean;
  distancia_media?: number | null; importe_medio?: number | null; propina_media?: number | null; pct_pago_tarjeta?: number | null;
}
export interface Respuesta {                     // 200 de POST /api/consultas (la Respuesta de la API, tal cual)
  resultado: 'permitida' | 'enmascarada'; consulta: Consulta; filas: Fila[];
  grupos_enmascarados: number; truncada: boolean; nota: string;
}
export interface Decision {                      // 403 de POST /api/consultas (la Decision de la API, tal cual)
  resultado: 'rechazada'; motivos: string[]; alternativa: Consulta | null;
}

export interface Servicio { nombre: string; job: string; estado: 'ok' | 'caido' | 'desconocido'; enlace?: string }
export interface Panel {                         // GET /api/panel
  ultimo_dia: { historico: UltimoDia | null; tiempo_real: UltimoDia | null };
  frescura_tiempo_real: { instante: string | null; segundos: number | null };   // desde publico_ultima_actualizacion_timestamp_segundos
  consultas_24h: { permitida: number; enmascarada: number; rechazada: number } | null;   // increase(acceso_consultas_total[24h]) por resultado
  servicios: Servicio[];                                                        // `up` por job en Prometheus + GET /salud de las APIs
  enlaces: Record<'grafana' | 'airflow' | 'spark' | 'chatbot' | 'chatbot_rag' | 'api_acceso' | 'api_captura', string>;
  prometheus_disponible: boolean;
  acceso_disponible: boolean;                    // false si la API de acceso no ha respondido (distinto de «sin datos»)
}
// solo grupos visibles; los enmascarados se cuentan (grupos_enmascarados), nunca se suman
export interface UltimoDia { dia: string; por_barrio: Record<string, number>; total: number; grupos_enmascarados: number }

export interface TiempoReal {                    // GET /api/tiempo-real?horas=6 (1…48)
  acceso_disponible: boolean;
  frescura: Panel['frescura_tiempo_real'];
  ultimo_dia: string | null;                     // último día con datos en tr_viajes_dia_barrio
  por_hora: { hora: string; n_viajes: number; grupos: number; grupos_enmascarados: number }[];   // últimas N horas con datos, solo visibles
  por_zona_ultima_hora: Fila[];                  // las filas de la última hora (hora_zona, fuente tiempo_real)
}

export interface AuditoriaResumen {              // GET /api/auditoria/resumen?horas=24
  desde: string; hasta: string; total: number;
  resultados: Record<string, number>; clientes: Record<string, number>;
  motivos: { motivo: string; cantidad: number }[];          // tipo de motivo (antes de ': '), como scripts/informe_auditoria.py
  disponible: boolean;
}
export interface DecisionAuditada {              // GET /api/auditoria/decisiones?horas=24&resultado=&cliente=&limite=100
  instante: string; cliente: string; componente: string; resultado: string; motivos: string[];
  consulta: Record<string, unknown>; alternativa: Consulta | null; filas_devueltas?: number; grupos_enmascarados?: number;
}
export interface Carga {                         // GET /api/auditoria/cargas
  lote: string; entrada: string; origen: string; filas: number; validos: number; rechazados: number;
  motivos: Record<string, number>; grupos_publicados: Record<string, number>; grupos_suprimidos: Record<string, number>;
  grupos_complementarios?: Record<string, number>; version_reglas: number; instante: string;
}

export interface EjecucionAirflow {              // GET /api/operaciones/airflow/ejecuciones  (últimas 20 de pids_carga_historica)
  dag_run_id: string; estado: string; conf: Record<string, unknown>; inicio: string | null; fin: string | null;
}
// GET  /api/operaciones/airflow/muestra -> {bloqueada, motivo}
// POST /api/operaciones/airflow/cargas {mes: '2020-01', muestra: boolean} -> EjecucionAirflow (202; 409 si la muestra pisaría el histórico)
export interface Simulacion {                    // GET /api/operaciones/simulacion · POST (inicia) · DELETE (para)
  activa: boolean; lote: string | null; fichero: string | null; enviados: number; total: number;
  ritmo: number; inicio: string | null; fin: string | null; error: string | null;
}
// POST /api/operaciones/simulacion {fichero: 'yellow_tripdata_2020_muestra.csv', ritmo?: 50, maximo?: number} -> Simulacion (202)
// Captura en directo (grafo, «Capturar datos»): GET /api/operaciones/captura -> {disponible, primer_dia, ultimo_dia, reloj,
//   velocidad_por_defecto, velocidad_maxima} · POST {velocidad?: 60, desde?} -> Simulacion (202) con modo: 'directo', reloj
//   (hora de 2020) y velocidad; total 0 · DELETE -> Simulacion. Comparte estado con la simulación: una sola a la vez (409).
// Los ficheros permitidos son solo los de data/muestra (GET /api/operaciones/simulacion/ficheros -> string[]).

// --- chat (F2) ---
export interface Motor { id: 'ollama' | 'rag'; nombre: string; modelo: string; disponible: boolean; descripcion: string }
// GET /api/chat/motores -> Motor[]
// POST /api/chat/sesiones {motor} -> 201 {id: string, motor: Motor['id']} (422 motor desconocido, 409 no disponible,
//      503 si el motor no arranca)   · DELETE /api/chat/sesiones/{id} -> 204
// POST /api/chat/sesiones/{id}/mensajes {texto} -> text/event-stream con los eventos de abajo
// POST /api/chat/sesiones/{id}/alternativa -> el mismo flujo, ejecutando la alternativa pendiente de la sesión
export interface EventoPaso { nombre: string; argumentos: Record<string, unknown>; resultado: string; segundos: number }
export interface EventoRespuesta {
  respuesta: string;                             // Markdown (tal cual lo produce el agente: tablas, 🔒, pie de fuente)
  bloqueo: string | null; pasos_llm: number; segundos: number; tokens: number | null;
  alternativa: Consulta | null; alternativa_descripcion: string | null;      // agente.describir(alternativa)
  fuentes: { titulo: string; fuente: string; tipo: string }[];             // solo el motor rag
}
// eventos SSE: `paso` (EventoPaso), `respuesta` (EventoRespuesta), `error` ({detail}); sse-starlette envía además
// comentarios `: ping` cada 15 s, que el cliente ignora. Dos mensajes a la vez sobre la misma sesión -> 409;
// alternativa sin rechazo pendiente -> 400. En un rechazo del filtro previo el agente no llama a `ejecutar`, pero su
// `Llamada` solicitud_individual se emite igualmente como `paso` (segundos 0) para que se vea que quedó auditado.
// `EventoPaso.resultado` resume filas y enmascarados («enmascarada (8 filas, 1 enmascarada)», «rechazada», «N zonas»).
// `tokens` es 0 (no null) en los turnos que no llaman al LLM.

// --- observabilidad (los cuadros de Grafana, dibujados por la SPA) ---
// GET /api/observabilidad/cuadros -> {uid, titulo, periodo}[]            (los ocho de observabilidad/grafana/dashboards)
// GET /api/observabilidad/cuadros/{uid} -> Cuadro (404 si el uid no es de un cuadro)
export interface PanelCuadro {
  id: number; tipo: 'fila' | 'stat' | 'serie' | 'barras' | 'tarta' | 'texto' | 'alertas';
  titulo: string; descripcion: string; x: number; y: number; ancho: number; alto: number;   // gridPos de Grafana (24 columnas)
  unidad: string; color: string | null; umbrales: {color: string; desde: number | null}[];
  mapeos: Record<string, {texto: string | null; color: string | null}>; colores: Record<string, string>; texto: string | null;
  valores?: {nombre: string; valor: number | null}[];     // stat, barras, tarta
  chispa?: number[];                                        // stat que no depende del periodo
  series?: {nombre: string; puntos: [number, number | null][]}[];   // serie: segundos y valor, unos 60 puntos
  alertas?: {nombre: string; estado: string; resumen: string}[];    // alertas
  error?: string;                                           // «Prometheus no responde», «Grafana no responde»
}
export interface Cuadro { uid: string; titulo: string; periodo: string; actualizado: number; disponible: boolean;
  paneles: PanelCuadro[]; grabado?: string }                // grabado: solo en la demostración

// --- gestos de la parte 1 ---
// POST /api/gestos {gesto: 'ok'|'paper'|'rock'|'rockandroll'|'scissors'|'thumbsup', confianza: 0..1,
//                   dispositivo: 'portal-[a-z0-9]{6,32}'} -> 202 {enviado: boolean}   (demostración: {enviado: false, demostracion: true})
// GET /api/gestos/pregunta?anterior=… -> {pregunta}: la de ✌️, al azar (`pregunta_al_azar` de parte3_chatbot/gestos.py);
//   en la demostración, las grabadas de `preguntas`, una detrás de otra
// GET /api/gestos/stream -> text/event-stream: `gesto` {gesto, confianza, dispositivo, instante}; 503 sin clave de
//   gestos; 404 en la demostración (el portal deja de escuchar)
```

Detalles de implementación que no se negocian:

- `POST /api/consultas` reenvía el cuerpo a `POST /consultas` de la API de acceso y devuelve **el mismo código y el mismo
  cuerpo** (200 con `Respuesta`, 403 con `Decision`, 422 con la validación). No relaja ni filtra nada.
- `GET /api/panel` y `GET /api/tiempo-real` obtienen las cifras con **consultas normales a la API de acceso** (nivel
  `dia_barrio` u `hora_zona`, fuente correspondiente) y solo suman los grupos visibles (`suprimido: false`): los
  enmascarados se cuentan, nunca se suman. Prometheus solo aporta estado, frescura y contadores de consultas.
- Auditoría: `pymongo` con el usuario `pids_auditor`; consultas con `instante` en el rango y orden descendente; `_id`
  fuera. El resumen agrupa los motivos por su tipo (texto antes de `': '`), como `scripts/informe_auditoria.py`.
- Airflow 3: `POST {AIRFLOW_URL}/auth/token {"username","password"}` → `access_token`; luego `Authorization: Bearer`.
  Ejecuciones: `GET /api/v2/dags/pids_carga_historica/dagRuns?order_by=-logical_date&limit=20`. Lanzar:
  `POST /api/v2/dags/pids_carga_historica/dagRuns {"logical_date": null, "conf": {"mes": "2020-01", "muestra": false}}`.
  El BFF valida `mes` con `^2020-(0[1-9]|1[0-2])$`.
- Simulador: reimplementación con la biblioteca estándar (`csv`, `datetime`, `httpx`), sin pandas: lee el CSV de
  `data/muestra`, ordena por `tpep_pickup_datetime` (formato `%m/%d/%Y %I:%M:%S %p`), envía lotes de 100 viajes a
  `POST {CAPTURA_URL}/viajes` con `{"lote": "portal-<fichero>-<fecha>", "viajes": [...]}` al ritmo pedido, en una tarea
  `asyncio` en segundo plano; una sola simulación activa a la vez (`409` si ya hay una).
- Chat: cada sesión guarda un agente vivo (`parte3_chatbot.agente.Agente` con `ollama.AsyncClient` para `ollama`;
  `parte3_chatbot_rag.fabrica.agente_rag` para `rag`, **solo si ese módulo se puede importar**: si no, el motor `rag`
  aparece con `disponible: false`). Los pasos de las herramientas se emiten en directo pasando un `ejecutar` propio a
  `agente.responder(texto, ejecutar=...)`, igual que hace Chainlit. Las sesiones viven en memoria y caducan a las 2 h.
  El texto de la respuesta se muestra **tal cual**: las barreras de privacidad ya están dentro del agente y no se
  reimplementan aquí.
- Observabilidad: el BFF lee los JSON de los cuadros de Grafana (`parte2_plataforma/observabilidad/grafana/dashboards`)
  y ejecuta en Prometheus **solo** sus consultas (`$__range` se sustituye por el periodo del cuadro): la SPA pide un uid,
  nunca una consulta. Series con `query_range` (paso ≥ 15 s), stat, barras y tarta con `query`, alertas con
  `GET {GRAFANA_URL}/api/prometheus/grafana/api/v1/rules`. Leyendas repetidas se distinguen con la etiqueta que las
  diferencia (la instancia, si vale). Caché de 10 s por cuadro; Prometheus caído → 200 con `error` en cada panel.
- Gestos: el BFF nunca recibe la imagen ni los puntos de la mano, solo la etiqueta y la confianza. Los reenvía a
  `POST {CAPTURA_URL}/gestos` con `modelo: 'portal · mlp_muneca_escala_rot'` y retransmite `GET {CAPTURA_URL}/gestos/stream`
  (solo `gesto`, `confianza`, `dispositivo` e `instante`; el cliente que lo envió no sale). Sin clave o con la captura
  caída, `enviado: false`: el gesto sigue actuando en el navegador.

## 6. La SPA (`parte4_frontend/web`)

Rutas (`react-router`), todas protegidas por la guardia de sesión salvo `/acceso`:

| Ruta | Página (fichero que F0 deja vacío y F3/F4 rellenan) | Contenido |
|---|---|---|
| `/acceso` | `paginas/acceso/PaginaAcceso.tsx` (F0) | Formulario de contraseña del portal |
| `/` | `paginas/panel/PaginaPanel.tsx` (F3) | KPIs del último día publicado (total y por barrio, barras), frescura del tiempo real, decisiones de las últimas 24 h, estado de servicios, accesos directos |
| `/explorador` | `paginas/explorador/PaginaExplorador.tsx` (F3) | Formulario de consulta (nivel, fuente, fechas y horas alineadas al nivel, zona con buscador, barrios, métricas) → tabla ordenable con los grupos enmascarados marcados (`oculto`) + gráfico (líneas por hora, barras por barrio, matriz origen→destino para flujos) + nota de privacidad. Un 403 se muestra como tarjeta «Consulta rechazada» con los motivos y un botón «Consultar la alternativa» que rellena y lanza la alternativa |
| (sin ruta; antes `/asistente`, que hoy redirige a `/` con el panel abierto) | `paginas/asistente/Asistente.tsx` dentro de `componentes/shell/PanelAsistente.tsx` (T16) | TAXI AI: botón fijo abajo a la derecha en todas las páginas; el panel entra desde el borde derecho con el chat: selector de motor (Ollama / RAG), burbujas con Markdown, pasos de herramientas en directo (SSE), botón de alternativa tras un rechazo, «Fuentes» y tokens/segundos por turno. Cerrarlo lo esconde sin navegar y conserva la conversación |
| `/tiempo-real` | `paginas/tiempo-real/PaginaTiempoReal.tsx` (F3) | Frescura con semáforo, viajes por hora (gráfico de barras), tabla de la última hora por zona; refresco cada 30 s |
| `/privacidad` | `paginas/privacidad/PaginaPrivacidad.tsx` (F4) | Reglas E3 en lenguaje claro (k = 10, niveles, granularidad, rango, campos prohibidos; leídas de `/api/catalogo`), resumen de auditoría con filtros por horas/resultado/cliente, tabla de decisiones, cargas históricas con sus grupos publicados/suprimidos |
| `/operaciones` | `paginas/operaciones/PaginaOperaciones.tsx` (F4) | Lanzar una carga histórica (mes o muestra) y ver las ejecuciones de Airflow; iniciar/parar el simulador con barra de progreso |
| `/grafo` (antes `/documentacion`, que redirige) | `paginas/documentacion/PaginaDocumentacion.tsx` | Grafo de la plataforma a pantalla completa: qué hace cada pieza, tramos iluminados según lo que está en marcha, «Capturar datos» (captura en directo) y zoom con rueda, gesto o botones |
| `/observabilidad` | `paginas/observabilidad/PaginaObservabilidad.tsx` | Los ocho cuadros de Grafana dibujados con los componentes del portal (misma rejilla y paneles, animados), refresco cada 30 s; «Abrir en Grafana» solo desde el equipo de la plataforma |
| `*` | (F0) | Página «No encontrado» |

Estructura de `web/src` (F0 la crea; los demás solo escriben dentro de sus carpetas):

```
src/
├── main.tsx · App.tsx · rutas.tsx
├── estilos/globales.css          tema (variables CSS de shadcn con la paleta corporativa), fuente Inter (@fontsource)
├── api/cliente.ts                fetch con credenciales, JSON, errores tipados (ErrorApi con status y detail), 401 → /acceso
├── api/tipos.ts                  los tipos del §5
├── api/sesion.ts                 useSesion, iniciarSesion, cerrarSesion
├── api/{panel,consultas,tiempoReal}.ts (F3) · {chat,auditoria,operaciones}.ts (F4)     hooks de TanStack Query
├── componentes/ui/**             shadcn/ui (button, card, badge, table, tabs, select, input, label, dialog, sheet,
│                                 tooltip, skeleton, separator, dropdown-menu, scroll-area, switch, progress, sonner)
├── componentes/shell/**          AppShell, BarraLateral, Cabecera (estado de servicios, cerrar sesión), Pie (aviso E3),
│                                 GuardiaSesion, Encabezado de página (título + descripción + acciones)
├── componentes/graficos/** (F3) · componentes/datos/** (F3) · componentes/chat/** (F4)
└── paginas/<sección>/Pagina<Sección>.tsx (+ subcomponentes y *.test.tsx)
```

Estados obligatorios en todas las páginas: **cargando** (skeletons), **error** (tarjeta con el `detail` y botón
«Reintentar»), **sin datos** y **servicio no disponible** (cuando el BFF devuelve `disponible: false`/`null`).
Accesibilidad básica: etiquetas en los formularios, foco visible, contraste AA, tablas con `<th scope>`.

## 7. Sistema de diseño

Marca: empresa de taxis de Nueva York con una plataforma de datos que presume de privacidad. Serio, denso en datos,
cálido por el amarillo del taxi como acento (nunca como fondo grande).

| Token | Valor | Uso |
|---|---|---|
| `--primario` | `#0B1F3A` (azul marino) | Barra lateral, títulos, botones primarios |
| `--acento` | `#F5B400` (amarillo taxi) | Elemento activo del menú, indicadores, gráficos (serie principal) |
| `--fondo` / `--superficie` | `#F4F6F9` / `#FFFFFF` | Fondo de la app / tarjetas |
| `--texto` / `--texto-suave` | `#111827` / `#6B7280` | Texto / etiquetas secundarias |
| `--borde` | `#E5E7EB` | Bordes de tarjetas y tablas |
| `--ok` / `--aviso` / `--peligro` | `#15803D` / `#B45309` / `#B91C1C` | Estado de servicios, semáforo de frescura, rechazos |
| `--enmascarado` | `#7C3AED` (violeta) | Grupos `oculto`: chip «enmascarado por privacidad» |
| Tipografía | Inter (`@fontsource/inter`), 14 px base, títulos 20/24/30 semibold; cifras con `font-variant-numeric: tabular-nums` | |
| Radio / sombra | 8 px / sombra suave en tarjetas | |
| Gráficos | Recharts; serie principal en `--acento`, secundarias en azules; grupos enmascarados en `--enmascarado` con patrón o barra vacía | |

Los tokens se declaran como variables CSS en `estilos/globales.css` y se mapean a las variables de shadcn
(`--primary`, `--accent`, `--destructive`, …), de modo que todos los componentes de `ui/` los heredan. Modo oscuro:
opcional, si sale gratis con las variables.

Formato de cifras: español (`1.234.567`, `2,07 $`, `35,4 %`), fechas `dd/mm/yyyy` y horas `HH:mm`; helpers en
`componentes/datos/formato.ts` (F3) que F4 también puede importar.

Dependencias que F0 instala (versiones publicadas hace ≥ 7 días, fijadas en `package-lock.json`): `react`, `react-dom`,
`react-router` (v7, modo biblioteca), `@tanstack/react-query`, `recharts`, `react-markdown` + `remark-gfm`,
`lucide-react`, `date-fns`, `sonner`, `clsx`, `tailwind-merge`, `class-variance-authority`, `@fontsource/inter`, `tailwindcss`
(v4 con `@tailwindcss/vite`), `shadcn` (CLI) con sus `@radix-ui/*`; desarrollo: `typescript`, `vite`, `@vitejs/plugin-react`,
`vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, `eslint` +
`typescript-eslint` + `eslint-plugin-react-hooks`.

Python, grupo `frontend` en `pyproject.toml` (F0): `fastapi`, `uvicorn[standard]`, `httpx`, `pymongo`, `sse-starlette`,
`pydantic`. La imagen instala además los grupos `chatbot` (agente de Ollama) y `rag` (motor RAG del asistente):
`ARG GRUPOS="frontend chatbot rag"` en el Dockerfile, que copia `parte3_chatbot` y `parte3_chatbot_rag`.

## 8. Comandos

```bash
# BFF en el host (lee .env y usa los puertos publicados)
uv run uvicorn parte4_frontend.bff.app:app --port 8020 --reload
uv run pytest -q tests/test_frontend_bff_*.py

# SPA en el host
cd parte4_frontend/web && npm ci && npm run dev          # http://localhost:5173 (proxy /api -> 8020)
npm run lint && npm test -- --run && npm run build

# Todo junto, en Docker (solo desde la carpeta principal del repositorio)
make frontend            # docker compose --profile frontend up -d --build frontend  -> http://localhost:8020
```

Plataforma levantada en este equipo (para pruebas manuales desde el host, claves en `.env`): API de acceso
`127.0.0.1:8002`, captura `:8001`, Grafana `:3000`, Airflow `:8085`, MongoDB `:27018`, chatbots `:8010` y `:8011`,
portal `:8020`. Prometheus, Spark, Ollama, Qdrant y Kafka no se publican (no tienen login). Los datos publicados
son de todo 2020 (23,7 M de viajes; k = 10).
