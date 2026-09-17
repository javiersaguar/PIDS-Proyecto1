# Atajos del proyecto. Ejecutar dentro de Ubuntu (WSL2) desde la raíz del repositorio.
# `make` sin argumentos muestra la ayuda.

MES ?= 2020-01
FUENTE ?= parquet
FICHERO ?= data/muestra/yellow_tripdata_2020_muestra.csv
RITMO ?= 50
SIN_GPU ?=

COMPOSE := docker compose $(if $(SIN_GPU),-f docker-compose.yml -f docker-compose.sin-gpu.yml,)
PERFILES_TODO := --profile spark --profile airflow --profile observabilidad --profile chatbot

.DEFAULT_GOAL := ayuda
.PHONY: ayuda entorno sync test test-spark construir nucleo spark airflow observabilidad chatbot \
	    herramientas todo parar estado logs tiempo-real simular historico historico-muestra \
	    datos-muestra descargar borrar-todo

ayuda: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-18s %s\n", $$1, $$2}'

# --- preparación ----------------------------------------------------------------------------
entorno: ## Genera .env con claves aleatorias (no sobrescribe uno existente)
	python3 scripts/generar_env.py

sync: ## Crea o actualiza el entorno Python local (uv)
	uv sync

test: ## Tests de Python
	uv run pytest -q

test-spark: ## Tests de Scala (dentro de Docker, no hace falta sbt)
	docker build --target compilacion --build-arg EJECUTAR_TESTS=true -f parte2_plataforma/spark/Dockerfile -t pids/spark-tests:local .

construir: ## Construye todas las imágenes del proyecto
	$(COMPOSE) $(PERFILES_TODO) --profile simulador build

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

herramientas: _env ## Consola de Redpanda (http://localhost:8088). Muestra mensajes crudos: solo desarrollo
	$(COMPOSE) --profile herramientas up -d

todo: _env ## Toda la plataforma
	$(COMPOSE) $(PERFILES_TODO) up -d

parar: ## Para todos los servicios (conserva los datos)
	$(COMPOSE) $(PERFILES_TODO) --profile herramientas --profile simulador down

estado: ## Estado de los servicios
	$(COMPOSE) $(PERFILES_TODO) --profile herramientas ps

logs: ## Logs en directo (S=servicio para uno solo)
	$(COMPOSE) $(PERFILES_TODO) logs -f --tail=100 $(S)

borrar-todo: ## Para todo y BORRA los volúmenes (datos, usuarios, modelos). Pide confirmación
	@read -p "Se borrarán todos los datos de la plataforma. Escribe 'borrar' para seguir: " r && [ "$$r" = borrar ]
	$(COMPOSE) $(PERFILES_TODO) --profile herramientas --profile simulador down -v

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

descargar: ## Descarga un mes a data/crudo (MES=2020-01 FUENTE=parquet|api)
	uv run python scripts/descargar_datos.py --fuente $(FUENTE) --meses $(MES)

_env:
	@test -f .env || (echo "Falta .env: ejecuta 'make entorno'" && exit 1)
