# Próximas tareas

Lista viva de las **10 tareas siguientes**, en orden de prioridad. Si te pones a trabajar, coge la
primera que esté libre.

## Cómo se usa

1. **Coge una tarea:** pon tu nombre en «Responsable» y el estado en `en curso`.
2. **Al terminar:** marca `hecha ✅`, muévela al final, a «Tareas terminadas», con la fecha, y escribe
   la entrada correspondiente en [`BITACORA.md`](BITACORA.md) (esta lista dice *qué* hacer; la bitácora
   cuenta *qué se hizo*).
3. **Si añades trabajo nuevo:** apúntalo abajo, en «Ideas y trabajo futuro», y súbelo a la lista de 10
   solo cuando quede hueco. La lista no debe crecer: si todo es urgente, nada lo es.
4. **Si la dejas a medias:** deja el estado en `en curso`, escribe en «Notas» qué falta exactamente y
   cuéntalo en la bitácora.
5. **Si trabajas con una IA:** dale primero `BITACORA.md` y este fichero; así sabe el estado real y la
   tarea concreta, sin reinventar lo ya hecho.

| Estado | Significado |
|---|---|
| `libre` | Nadie la ha cogido |
| `en curso` | Alguien está con ella (mira «Notas») |
| `bloqueada` | Depende de otra tarea o de algo externo |
| `hecha ✅` | Terminada y con entrada en la bitácora |

---

## T01 · Copia de seguridad del dataset de gestos

- **Estado:** libre · **Responsable:** — · **Estimación:** 30 min · **Dificultad:** baja
- **Por qué:** las 3000 imágenes y las 5 tomas originales **solo existen en el portátil de Javier**
  (`C:\Users\Javier\PIDS_HandPose`), porque no caben en el repositorio. Si se pierde ese disco, se pierde
  el dataset del proyecto y no se puede volver a grabar (cinco personas, una tarde).
- **Qué hay que hacer:**
  1. Comprimir `kit-grabacion\HAR_mediapipe\data` (las 5 tomas con su metadata.json).
  2. Subirlo a un sitio compartido del grupo (Drive de la universidad, por ejemplo) y anotar el enlace
     en `parte1_gestos/README.md`.
  3. Comprobar que alguien más del grupo puede descargarlo y ejecutar `preprocesar.py` con él.
- **Hecha cuando:** otro miembro del grupo ha reproducido el preprocesado desde la copia.
- **Dónde:** `parte1_gestos/README.md`

## T02 · Curva privacidad-utilidad y ataque por diferencia

- **Estado:** en curso · **Responsable:** bloque «privacidad» (rama `tarea/privacidad`) · **Estimación:** 4 h · **Dificultad:** media
- **Por qué:** con el año completo cargado sabemos que k = 10 oculta el 60 % de los grupos finos pero
  solo el 4,9 % de los viajes (`docs/metricas_calidad.md`). Falta justificar el valor de k y comprobar
  el riesgo que ya está apuntado en `docs/escenario_E3.md`: restando niveles se puede acotar un grupo
  suprimido.
- **Qué hay que hacer:**
  1. Un trabajo Spark de análisis (`pids.AnalisisPrivacidad`) que, sin publicar nada ni cambiar
     `config/privacidad.json`, calcule grupos y viajes publicados con k = 5, 10, 20 y 50 sobre los viajes
     válidos del año: es la curva privacidad-utilidad.
  2. Escribir un script que intente el ataque usando solo la API: restar al total del día y barrio los
     grupos hora-zona visibles y contar cuántos grupos suprimidos quedan revelados exactamente.
  3. Si sale, proponer la mitigación (suprimir también el segundo grupo más pequeño, o añadir ruido) y,
     si da tiempo, implementarla y medir su coste.
- **Hecha cuando:** la curva está en `docs/metricas_calidad.md` y el resultado del ataque, con su
  mitigación, en `docs/escenario_E3.md`.
- **Dónde:** `config/privacidad.json`, `scripts/`, `docs/`

## T03 · Medir las 3 métricas de calidad

- **Estado:** en curso · **Responsable:** M1 bloque «privacidad» (API) y «chatbot» (chatbot); M3 bloque «observabilidad» · **Estimación:** 4 h · **Dificultad:** media
- **Por qué:** el enunciado las pide definidas **y medidas**; están definidas en
  `docs/metricas_calidad.md` pero sin datos.
- **Qué hay que hacer:**
  1. `scripts/bateria_privacidad.py`: 20-30 peticiones trampa (viajes concretos, horas con minutos,
     destino por zona, campos prohibidos, rangos enormes) contra la API y contra el chatbot; contar
     cuántas devuelven algo que no debería (M1).
  2. Sacar de `auditoria.cargas` el % de viajes en grupos publicados por nivel, con k = 5, 10 y 20 (M2).
  3. Medir la latencia del tiempo real: marca de tiempo al enviar y primera aparición del agregado;
     percentiles 50 y 95 (M3).
- **Hecha cuando:** `docs/metricas_calidad.md` tiene la tabla de resultados y el script está en el repo.
- **Dónde:** `scripts/`, `docs/metricas_calidad.md`

## T04 · Alertas en Grafana

- **Estado:** en curso · **Responsable:** bloque «observabilidad» (rama `tarea/observabilidad`) · **Estimación:** 2 h · **Dificultad:** media
- **Por qué:** «Alertas» es una de las cajas del esquema de la asignatura y suma en la evaluación; el
  panel ya existe, las alertas no.
- **Qué hay que hacer:** provisionar por ficheros (no a mano en la interfaz) al menos tres reglas:
  1. muchas consultas rechazadas en poco tiempo (posible intento de reidentificación),
  2. el tiempo real no publica agregados desde hace más de 5 minutos,
  3. algún servicio caído (`up == 0`).
- **Hecha cuando:** las alertas aparecen solas al levantar Grafana y se puede provocar una a propósito.
- **Dónde:** `parte2_plataforma/observabilidad/grafana/provisioning/alerting/`

## T05 · Probar y pulir los 8 casos de uso del chatbot

- **Estado:** en curso · **Responsable:** bloque «chatbot» (rama `tarea/chatbot`) · **Estimación:** 4 h · **Dificultad:** media
- **Por qué:** es lo que se ve en la demo y lo que evalúan en la parte 3.
- **Qué hay que hacer:**
  1. Pasar los 8 casos de `docs/casos_uso.md` uno por uno (con `comprobar_agente.py` o en la interfaz).
  2. Ajustar `prompts.py` donde el modelo se equivoque (fechas, ids de zona, niveles).
  3. Guardar capturas de cada caso en `docs/capturas/`.
- **Hecha cuando:** los 8 casos funcionan y hay captura de cada uno.
- **Dónde:** `parte3_chatbot/prompts.py`, `docs/casos_uso.md`, `docs/capturas/`

## T06 · Integración de los gestos (última fase del esquema)

- **Estado:** bloqueada por T05 · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** es la caja «Integración» de la diapositiva 5 (opcional, pero puntúa).
- **Qué hay que hacer:**
  1. Llamar a `EmisorGestos.observar(pred, conf)` desde `parte1_gestos/demo/src/demo-gestures-PIDS.py`.
  2. `GESTOS_ACTIVOS=true` en `.env` y reiniciar el chatbot.
  3. Probar el ciclo completo: el bot propone una alternativa → 👍 la ejecuta, ✋ la cancela.
- **Hecha cuando:** se graba un vídeo corto en el que un gesto confirma una consulta del chatbot.
- **Dónde:** `integracion/`, `parte1_gestos/demo/src/`

## T07 · Revisión de la auditoría de privacidad

- **Estado:** en curso · **Responsable:** bloque «observabilidad» (rama `tarea/observabilidad`) · **Estimación:** 2 h · **Dificultad:** baja
- **Por qué:** E3 pide registrar las decisiones; ya se guardan, pero no hay forma cómoda de revisarlas.
- **Qué hay que hacer:** un panel o un pequeño informe (`scripts/informe_auditoria.py`) que use el
  usuario `pids_auditor` (solo lectura) y muestre consultas por resultado, clientes y los rechazos
  recientes con sus motivos.
- **Hecha cuando:** se puede responder «¿qué se ha rechazado hoy y por qué?» en un comando.
- **Dónde:** `scripts/`, `parte2_plataforma/observabilidad/`

## T08 · Repaso de seguridad y modelo de amenazas

- **Estado:** libre · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** «elementos de autenticación / seguridad» puntúa, y conviene tener escrito qué se protege
  y qué no.
- **Qué hay que hacer:**
  1. Revisar qué puertos se publican y con qué credenciales (la pasarela REST de Spark y la consola de
     Redpanda no tienen autenticación: dejarlas solo en la red interna o detrás de un proxy).
  2. Rotación de claves: comprobar que `make entorno --forzar` y recrear volúmenes funciona.
  3. Escribir `docs/seguridad.md`: qué atacante se considera, qué se protege y qué queda fuera.
- **Hecha cuando:** existe `docs/seguridad.md` y no hay ningún servicio sin autenticación accesible
  fuera de Docker.
- **Dónde:** `docker-compose.yml`, `docs/seguridad.md`

## T09 · Alta disponibilidad de la API de acceso

- **Estado:** libre · **Responsable:** — · **Estimación:** 3 h · **Dificultad:** media
- **Por qué:** es uno de los criterios adicionales del enunciado y ahora mismo la API es un único
  contenedor.
- **Qué hay que hacer:** dos réplicas de `acceso` detrás de un proxy (Caddy o Nginx), comprobar que se
  puede tirar una sin cortar el servicio, y documentar qué pasa con el resto de componentes (Spark
  standalone tiene un solo máster: apuntar la limitación).
- **Hecha cuando:** con una réplica parada, el chatbot sigue respondiendo.
- **Dónde:** `docker-compose.yml`, `docs/arquitectura.md`

## T10 · Entrega: vídeo y presentación

- **Estado:** libre · **Responsable:** — · **Estimación:** 6 h (entre varios) · **Dificultad:** baja
- **Por qué:** es lo que se entrega y se puntúa (diapositiva 10).
- **Qué hay que hacer:**
  1. Vídeo: levantar la plataforma, cargar datos, ver el panel, conversar con el chatbot (incluido un
     rechazo por privacidad) y, si está, el gesto.
  2. Presentación: reparto del trabajo, comparativa, arquitectura, casos de uso, demo y conclusiones.
  3. Repasar el checklist de `docs/plan.md`.
- **Hecha cuando:** el vídeo y las diapositivas están listos y enlazados desde el README.
- **Dónde:** `docs/`, README

---

## Ideas y trabajo futuro

- Privacidad diferencial (OpenDP) sobre los agregados, además del umbral k.
- Detectar patrones de consultas sospechosos por cliente (muchas consultas solapadas).
- Airflow: un DAG que cargue los 12 meses en cadena, con reintentos.
- Comparar la exportación completa con los Parquet mensuales de la TLC (¿mismos viajes?).
- Committer de S3A más rápido para las escrituras de Spark.

## Tareas terminadas

| Fecha | Tarea | Quién | Bitácora |
|---|---|---|---|
| 17/09/2026 | Estructura del repositorio y código base de la plataforma | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Parte 1 integrada (código y CSV generados) y bitácora | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Primer despliegue completo: histórico, tiempo real, Airflow y observabilidad | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Chatbot en marcha (CPU) con barrera contra cifras inventadas | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | Dataset completo ingerido y cargado: 23,7 M de viajes válidos en 2 min | Javier Saguar | entrada del 17/09 |
| 17/09/2026 | T01 Chatbot con GPU: toolkit de NVIDIA, `llama3.1:8b` y respuestas en 3-5 s | Javier Saguar | entrada del 17/09 |
| 18/09/2026 | T01 Parte 1 ejecutable desde el repositorio (sin rutas fijas) | Javier Saguar | entrada del 18/09 |
