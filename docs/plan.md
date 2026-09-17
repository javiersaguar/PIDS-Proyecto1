# Plan de trabajo

## Fases

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Repositorio, estructura, elección de escenario (E3) y de tecnologías | ✅ |
| 1 | Datos: descarga, esquema canónico, validación y perfilado | ✅ código base · ⏳ perfilar meses completos |
| 2 | Diseño: comparativa, arquitectura, reglas de privacidad, métricas | ✅ primera versión |
| 3a | Núcleo: S3, Redpanda, MongoDB, APIs de captura y acceso | ✅ código base · ⏳ primer despliegue |
| 3b | Spark: carga histórica y tiempo real (Scala, modo cluster) | ✅ código base · ⏳ compilar y probar en el clúster |
| 3c | Airflow: DAG de carga histórica | ✅ código base · ⏳ probar |
| 3d | Prometheus + Grafana: panel y alertas | ✅ panel · ⏳ alertas |
| 3e | Medición de las 3 métricas de calidad | ⏳ |
| 4 | Chatbot: casos de uso con LLM local | ✅ código base · ⏳ probar con Ollama y ajustar el prompt |
| 5 | Integración con la parte 1 (gestos) | ⏳ última (opcional) |
| 6 | Entrega: documentación, capturas, vídeo, presentación | ⏳ |

## Reparto propuesto (5 personas)

| Persona | Responsabilidad | Carpetas |
|---|---|---|
| 1 | Spark (Scala): histórico y tiempo real | `parte2_plataforma/spark` |
| 2 | Almacenamiento, cola y despliegue (Compose, S3, MongoDB, Redpanda) | `docker-compose.yml`, `parte2_plataforma/{s3,mongodb}` |
| 3 | APIs y reglas de privacidad | `parte2_plataforma/{captura,acceso,comun}`, `config/` |
| 4 | Airflow, Prometheus, Grafana y métricas de calidad | `parte2_plataforma/{airflow,observabilidad}`, `docs/metricas_calidad.md` |
| 5 | Chatbot, casos de uso e integración con los gestos | `parte3_chatbot`, `integracion` |

Documentación y presentación, entre todos.

## Forma de trabajar

- Una rama por tarea y *pull request* a `main`; el CI pasa los tests de Python y de Scala y valida
  el `docker-compose.yml`.
- Cambios pequeños y probados: `make test` antes de subir.
- Cada avance relevante se apunta en [`registro_avances.md`](registro_avances.md).

## Checklist de la entrega (diapositivas 6-10)

- [ ] Comparativa de soluciones evaluadas → `docs/comparativa.md`
- [ ] Elección de tecnologías justificada por la restricción
- [ ] Diseño de la arquitectura → `docs/arquitectura.md`
- [ ] Instrucciones de ejecución y despliegue → `README.md`
- [ ] 3 métricas de calidad medidas → `docs/metricas_calidad.md`
- [ ] Casos de uso del chatbot con acceso a los datos → `docs/casos_uso.md`
- [ ] Capturas o vídeo de los casos de uso
- [ ] Extras: varias opciones de almacenamiento ✅, visualización ✅, seguridad ✅, código propio ✅,
      despliegue automatizado ✅, nueva fuente de datos (zonas de la TLC) ✅, alta disponibilidad (parcial:
      driver supervisado)
