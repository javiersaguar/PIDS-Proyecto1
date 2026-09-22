# Atajos del proyecto. Ejecutar dentro de Ubuntu (WSL2) desde la raíz del repositorio.
# `make` sin argumentos muestra la ayuda.

MES ?= 2020-01
FUENTE ?= parquet
FICHERO ?= data/muestra/yellow_tripdata_2020_muestra.csv
RITMO ?= 50
SIN_GPU ?=

COMPOSE := docker compose $(if $(SIN_GPU),-f docker-compose.yml -f docker-compose.sin-gpu.yml,)
PERFILES_TODO := --profile spark --profile airflow --profile observabilidad --profile chatbot --profile rag \
		--profile frontend
PERFILES_UNA_VEZ := --profile herramientas --profile simulador --profile rag-indexar
WEB := parte4_frontend/web

.DEFAULT_GOAL := ayuda
.PHONY: ayuda entorno entorno-completar sync hooks test test-spark test-frontend construir nucleo spark airflow observabilidad \
	    chatbot chatbot-rag rag-indexar rag-comprobar rag-casos rag-bateria rag-comparar frontend frontend-dev \
	    herramientas todo parar estado logs tiempo-real simular historico historico-muestra \
	    datos-muestra descargar borrar-todo alta-disponibilidad

ayuda: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-18s %s\n", $$1, $$2}'

# --- preparación ----------------------------------------------------------------------------
entorno: ## Genera .env con claves aleatorias (no sobrescribe; FORZAR=1 regenera y obliga a recrear volúmenes)
	python3 scripts/generar_env.py $(if $(FORZAR),--forzar,)

entorno-completar: ## Añade a un .env existente las variables nuevas de .env.example (sin tocar las demás)
	python3 scripts/generar_env.py --completar

sync: hooks ## Crea o actualiza el entorno Python local (uv) y activa los hooks de Git
	uv sync

hooks: ## Activa los hooks del repositorio (.githooks): quitan coautorías y firmas automáticas de los commits
	git config core.hooksPath .githooks
	@echo "Hooks activos: .githooks (ver docs/repositorio.md)"

test: ## Tests de Python
	uv run pytest -q

test-spark: ## Tests de Scala (dentro de Docker, no hace falta sbt)
	docker build --target compilacion --build-arg EJECUTAR_TESTS=true -f parte2_plataforma/spark/Dockerfile -t pids/spark-tests:local .

test-frontend: ## Tests del portal web: BFF (pytest) y SPA (eslint + vitest; requiere `npm ci` en parte4_frontend/web)
	uv run pytest -q tests/test_frontend_bff_*.py
	cd $(WEB) && npm run lint && npm test -- --run

construir: ## Construye todas las imágenes del proyecto
	$(COMPOSE) $(PERFILES_TODO) $(PERFILES_UNA_VEZ) build

# --- servicios ------------------------------------------------------------------------------
nucleo: _env ## Levanta el núcleo: S3, Redpanda, MongoDB y las APIs
	$(COMPOSE) up -d --wait

spark: _env ## Núcleo + clúster Spark (máster y 2 workers)
	$(COMPOSE) --profile spark up -d

airflow: _env ## Núcleo + Spark + Airflow (http://localhost:8085)
	$(COMPOSE) --profile spark --profile airflow up -d

observabilidad: _env ## Núcleo + Prometheus y Grafana (http://localhost:3000)
	$(COMPOSE) --profile observabilidad up -d

chatbot: _env ## Núcleo + Ollama y chatbot (http://localhost:8010). SIN_GPU=1 para CPU
	$(COMPOSE) --profile chatbot up -d

chatbot-rag: _env ## Núcleo + Qdrant y chatbot RAG con LLM externo (http://localhost:8011). Requiere LLM_API_KEY
	$(COMPOSE) --profile rag up -d

frontend: _env ## Portal web (http://localhost:8020)
	$(COMPOSE) --profile frontend up -d --build frontend

frontend-dev: _env ## BFF del portal en el host con recarga (puerto 8020); la SPA, aparte: cd parte4_frontend/web && npm run dev
	@echo "BFF en http://localhost:8020. Prometheus, Ollama y Qdrant no están publicados: el chat y el pulso salen con «make frontend». En otra terminal: cd $(WEB) && npm run dev"
	uv run uvicorn parte4_frontend.bff.app:app --port 8020 --reload

herramientas: _env ## Consola de Redpanda en la red interna (no se publica: muestra mensajes crudos)
	$(COMPOSE) --profile herramientas up -d

todo: _env ## Toda la plataforma
	$(COMPOSE) $(PERFILES_TODO) up -d

parar: ## Para todos los servicios (conserva los datos)
	$(COMPOSE) $(PERFILES_TODO) $(PERFILES_UNA_VEZ) down

estado: ## Estado de los servicios
	$(COMPOSE) $(PERFILES_TODO) $(PERFILES_UNA_VEZ) ps

logs: ## Logs en directo (S=servicio para uno solo)
	$(COMPOSE) $(PERFILES_TODO) logs -f --tail=100 $(S)

borrar-todo: ## Para todo y BORRA los volúmenes (datos, usuarios, modelos). Pide confirmación
	@read -p "Se borrarán todos los datos de la plataforma. Escribe 'borrar' para seguir: " r && [ "$$r" = borrar ]
	$(COMPOSE) $(PERFILES_TODO) $(PERFILES_UNA_VEZ) down -v

# --- flujos de datos ------------------------------------------------------------------------
tiempo-real: ## Lanza el trabajo Spark de tiempo real (modo cluster, supervisado)
	$(COMPOSE) exec spark-master /opt/pids/lanzar.sh TiempoReal

simular: ## Envía viajes a la API de captura (FICHERO=... RITMO=viajes/s)
	SIMULADOR_FICHERO=$(FICHERO) SIMULADOR_RITMO=$(RITMO) $(COMPOSE) --profile simulador run --rm simulador

historico: ## Ejecuta en Airflow la carga histórica de un mes (MES=2020-01)
	$(COMPOSE) exec airflow-apiserver airflow dags trigger pids_carga_historica --conf '{"mes": "$(MES)", "muestra": false}'

historico-muestra: ## Carga histórica del CSV de muestra (rápida, para probar)
	$(COMPOSE) exec airflow-apiserver airflow dags trigger pids_carga_historica --conf '{"mes": "2020-01", "muestra": true}'

subir-csv: ## Sube un CSV/Parquet propio a la zona restringida de S3 (FICHERO=/ruta/al/fichero.csv)
	@test -n "$(FICHERO)" || (echo "Uso: make subir-csv FICHERO=/ruta/al/fichero.csv" && exit 1)
	docker compose run --rm -T -v "$(dir $(abspath $(FICHERO)))":/entrada:ro s3-init 		python -m parte2_plataforma.s3.subir_fichero "/entrada/$(notdir $(FICHERO))"

historico-fichero: ## Carga con Spark un fichero ya subido a S3 (RUTA=s3a://crudo/historico/... LOTE=nombre)
	@test -n "$(RUTA)" || (echo "Uso: make historico-fichero RUTA=s3a://crudo/historico/fichero.csv [LOTE=nombre]" && exit 1)
	docker compose exec spark-master /opt/pids/lanzar.sh CargaHistorica "$(RUTA)" "$(or $(LOTE),manual)"

datos-muestra: ## Perfila y valida el CSV de muestra
	uv run python scripts/perfilar_datos.py data/muestra/yellow_tripdata_2020_muestra.csv

.PHONY: auditoria latencia
auditoria: _env ## Informe de auditoría de las últimas 24 h (ARGS='--horas 8 --comprobar-permisos')
	uv run python scripts/informe_auditoria.py $(ARGS)

latencia: _env ## Mide captura → agregado (20 lotes; requiere un único TiempoReal activo; ARGS='--zona 265')
	uv run python scripts/medir_latencia_tiempo_real.py $(ARGS)

alta-disponibilidad: _env ## Carga contra la API de acceso mientras para y tira cada réplica (ARGS='--sin-chatbot')
	uv run python scripts/probar_alta_disponibilidad.py $(ARGS)

descargar: ## Descarga un mes a data/crudo (MES=2020-01 FUENTE=parquet|api)
	uv run python scripts/descargar_datos.py --fuente $(FUENTE) --meses $(MES)

# --- chatbot RAG (perfil rag) ---------------------------------------------------------------
rag-comprobar: _env ## Comprueba el proveedor LLM: modelos, chat, llamada a herramienta y embeddings (ARGS='--modelo qwen3.6')
	$(COMPOSE) --profile rag run --rm --no-deps chatbot-rag python comprobar_llm.py $(ARGS)

rag-indexar: _env ## Indexa en Qdrant el conocimiento y las fichas de agregados (ARGS='--solo fichas')
	$(COMPOSE) --profile rag-indexar run --rm rag-indexar python indexar.py $(ARGS)

rag-casos: _env ## Suite de casos de uso del chatbot RAG, desde el anfitrión; informe en informes/chatbot_rag (ARGS='--casos CU1 --detalle')
	uv run python parte3_chatbot_rag/casos_de_uso_rag.py $(ARGS)

rag-bateria: _env ## Batería de preguntas trampa (M1) del chatbot RAG, desde el anfitrión (ARGS='--detalle')
	uv run python parte3_chatbot_rag/bateria_trampa_rag.py --repeticiones 3 $(ARGS)

rag-comparar: _env ## Los dos chatbots (Ollama y RAG) sobre la misma suite y batería (ARGS='--solo casos --repeticiones 1')
	uv run python parte3_chatbot_rag/comparar.py $(ARGS)

_env:
	@test -f .env || (echo "Falta .env: ejecuta 'make entorno'" && exit 1)
