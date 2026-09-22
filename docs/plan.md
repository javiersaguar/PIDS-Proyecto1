# Plan de trabajo

## Fases

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Repositorio, estructura, elección de escenario (E3) y de tecnologías | ✅ |
| 1 | Datos: descarga, esquema canónico, validación y perfilado | ✅ año 2020 completo cargado |
| 2 | Diseño: comparativa, arquitectura, reglas de privacidad, métricas | ✅ primera versión |
| 3a | Núcleo: S3, Redpanda, MongoDB, APIs de captura y acceso | ✅ desplegado |
| 3b | Spark: carga histórica y tiempo real (Scala, modo cluster) | ✅ en el clúster, con supresión complementaria |
| 3c | Airflow: DAG de carga histórica | ✅ probado |
| 3d | Prometheus + Grafana: panel y alertas | ✅ panel y 3 alertas probadas |
| 3e | Medición de las 3 métricas de calidad | ✅ M1, M2 y M3 medidas |
| 4 | Chatbot: casos de uso con LLM local | ✅ 7 casos medidos (21/21) y batería trampa |
| 4b | Chatbot RAG: LangChain + Qdrant + LLM externo en la UE (Helmcode) | ✅ Vigente (22/09). La demo enseña los dos: Ollama (las preguntas no salen del equipo) y RAG. 21/21 y 0/105 |
| 5 | Integración con la parte 1 (gestos) | ✅ vídeo en `docs/capturas/cu8_gesto.mp4` |
| 6 | Entrega: documentación, capturas, vídeo, presentación | ⏳ |

## Reparto propuesto (a confirmar en la primera reunión)

| Persona | Responsabilidad | Carpetas |
|---|---|---|
| Javier Saguar | Spark (Scala): histórico y tiempo real; ya trae el contexto de la parte 1 | `parte2_plataforma/spark`, `parte1_gestos` |
| Alejandro Cuevas | Almacenamiento, cola y despliegue (Compose, S3, MongoDB, Redpanda) | `docker-compose.yml`, `parte2_plataforma/{s3,mongodb}` |
| Mónica Fernández | APIs y reglas de privacidad (el núcleo de E3) | `parte2_plataforma/{captura,acceso,comun}`, `config/` |
| Pedro José Orrego | Airflow, Prometheus, Grafana y las 3 métricas de calidad | `parte2_plataforma/{airflow,observabilidad}`, `docs/metricas_calidad.md` |
| Daniel Naval | Chatbot, casos de uso e integración con los gestos | `parte3_chatbot`, `integracion` |

Documentación y presentación, entre todos. Cada uno describe sus cambios en [`../BITACORA.md`](../BITACORA.md).

## Forma de trabajar

- Una rama por persona (tabla en el [README](../README.md#equipo-y-ramas)) y *pull request* a `main`; el
  CI pasa los tests de Python y de Scala y valida el `docker-compose.yml`.
- Cambios pequeños y probados: `make test` antes de subir.
- El trabajo del día a día se lleva en dos ficheros de la raíz: [`../TAREAS.md`](../TAREAS.md) (las 10
  tareas siguientes, con criterio de «hecha») y [`../BITACORA.md`](../BITACORA.md) (qué se hizo, por qué,
  cómo comprobarlo y qué quedó pendiente). Son también el contexto que se pasa a cualquier asistente de IA.

## Checklist de la entrega (diapositivas 6-10)

- [x] Comparativa de soluciones evaluadas → `docs/comparativa.md`
- [x] Elección de tecnologías justificada por la restricción → `docs/comparativa.md` (cada fila, frente a E3)
- [x] Diseño de la arquitectura → `docs/arquitectura.md`
- [x] Instrucciones de ejecución y despliegue → `README.md` («Puesta en marcha»: primera vez, cada día, usuarios y web pública)
- [x] 3 métricas de calidad medidas → `docs/metricas_calidad.md`
- [x] Casos de uso del chatbot con acceso a los datos → `docs/casos_uso.md`
- [ ] Capturas o vídeo de los casos de uso (capturas en `docs/capturas/` y vídeo del gesto, `cu8_gesto.mp4`; falta el vídeo de la demo, T10, con su guion en [`guion_demo.md`](guion_demo.md))
- [x] Extras: varias opciones de almacenamiento ✅, visualización ✅, seguridad ✅ ([`seguridad.md`](seguridad.md)), código propio ✅,
      despliegue automatizado ✅, nueva fuente de datos (zonas de la TLC) ✅, alta disponibilidad (API de acceso con
      dos réplicas y proxy, probada con carga: 0 fallos; driver de Spark supervisado; el resto en una instancia,
      ver [`arquitectura.md`](arquitectura.md#alta-disponibilidad))
