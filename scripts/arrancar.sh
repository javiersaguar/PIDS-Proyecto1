#!/usr/bin/env bash
# Levanta la plataforma entera tras encender el portátil y comprueba que todo responde.
#
#   make arrancar                 # todo + tiempo real + túnel (si hay datos de ngrok en .env)
#   make arrancar ARGS=--sin-tunel
#   SIN_GPU=1 make arrancar       # Ollama en CPU
#
# No borra nada: los volúmenes (datos, usuarios, modelos, índice del RAG) se conservan entre arranques.
# Es seguro lanzarlo con la plataforma ya en marcha: solo arranca lo que falte.
set -uo pipefail
cd "$(dirname "$0")/.."

TUNEL=1
for arg in "$@"; do
    case "$arg" in
        --sin-tunel) TUNEL=0 ;;
        *) echo "Opción desconocida: $arg (uso: arrancar.sh [--sin-tunel])"; exit 2 ;;
    esac
done

verde=$'\e[32m'; ambar=$'\e[33m'; rojo=$'\e[31m'; gris=$'\e[90m'; fin=$'\e[0m'
paso() { echo; echo "${gris}==>${fin} $*"; }
bien() { echo "   ${verde}✔${fin} $*"; }
aviso() { echo "   ${ambar}!${fin} $*"; AVISOS=$((AVISOS + 1)); }
fallo() { echo "   ${rojo}✘${fin} $*"; exit 1; }
AVISOS=0

COMPOSE=(docker compose)
if [[ -n "${SIN_GPU:-}" ]]; then
    COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.sin-gpu.yml)
fi

# --- 1. requisitos ----------------------------------------------------------------------------
paso "Requisitos"
[[ -f .env ]] || fallo "Falta .env: ejecuta 'make entorno' (y pega LLM_API_KEY y los datos de ngrok)"
bien ".env presente"

if ! docker info >/dev/null 2>&1; then
    echo "   Docker no responde: abre Docker Desktop en Windows. Esperando hasta 3 minutos…"
    for _ in $(seq 1 90); do
        docker info >/dev/null 2>&1 && break
        sleep 2
    done
    docker info >/dev/null 2>&1 || fallo "Docker sigue sin responder. Abre Docker Desktop y vuelve a lanzar 'make arrancar'"
fi
bien "Docker en marcha"

set -a
# shellcheck disable=SC1091
source .env
set +a

# --- 2. servicios -----------------------------------------------------------------------------
paso "Núcleo: S3, Redpanda, MongoDB y las APIs (espera a que estén sanos)"
"${COMPOSE[@]}" up -d --quiet-pull || fallo "El núcleo no ha arrancado: mira 'make logs'"
# No se usa `up --wait`: da por fallo que s3-init y redpanda-init terminen, aunque es lo que deben hacer
sano() {
    local id
    id=$("${COMPOSE[@]}" ps -q "$1" 2>/dev/null)
    [[ -n "$id" && "$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null)" == healthy ]]
}
for servicio in s3 redpanda mongo acceso-a acceso-b acceso captura; do
    for _ in $(seq 1 60); do sano "$servicio" && break; sleep 2; done
    sano "$servicio" || fallo "$servicio no está sano: mira 'make logs S=$servicio'"
done
bien "Núcleo sano"

paso "Resto de la plataforma: Spark, Airflow, observabilidad, chatbots y portal"
"${COMPOSE[@]}" --profile spark --profile airflow --profile observabilidad --profile chatbot --profile rag \
    --profile frontend up -d --quiet-pull || fallo "Algún servicio no ha arrancado: mira 'make estado' y 'make logs'"
bien "Servicios lanzados"

# --- 3. tiempo real en Spark ------------------------------------------------------------------
paso "Trabajo de tiempo real en Spark"
estado_spark() { "${COMPOSE[@]}" exec -T spark-master curl -sf http://127.0.0.1:8080/json/ 2>/dev/null; }
json=""
for _ in $(seq 1 45); do
    json=$(estado_spark)
    if [[ -n "$json" ]] && python3 -c 'import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get("aliveworkers", 0) >= 1 else 1)' "$json"; then
        break
    fi
    json=""
    sleep 2
done
if [[ -z "$json" ]]; then
    aviso "El máster de Spark no tiene workers todavía; lanza el tiempo real luego con 'make tiempo-real'"
elif python3 -c 'import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if any(x.get("mainclass") == "pids.TiempoReal" for x in d.get("activedrivers", [])) else 1)' "$json"; then
    bien "Ya estaba en marcha (no se lanza otro: la latencia se mide con uno solo)"
else
    if "${COMPOSE[@]}" exec -T spark-master /opt/pids/lanzar.sh TiempoReal >/dev/null 2>&1; then
        bien "Lanzado (supervisado: el máster lo relanza si cae)"
    else
        aviso "No se ha podido lanzar; prueba 'make tiempo-real'"
    fi
fi

# --- 4. túnel para la web de Vercel -----------------------------------------------------------
paso "Túnel para la web pública (Vercel)"
if [[ "$TUNEL" == 0 ]]; then
    bien "No se toca el túnel (--sin-tunel); para apagarlo: make tunel-parar"
elif [[ -n "${NGROK_AUTHTOKEN:-}" && -n "${NGROK_DOMINIO:-}" ]]; then
    if "${COMPOSE[@]}" --profile tunel up -d --no-deps --quiet-pull tunel >/dev/null 2>&1; then
        bien "Túnel en marcha: https://${NGROK_DOMINIO} (la web de Vercel pasa a «En vivo»)"
    else
        aviso "El túnel no arranca: mira 'make logs S=tunel'"
    fi
else
    bien "Sin datos de ngrok en .env: la web pública muestra la instantánea"
fi

# --- 5. comprobaciones ------------------------------------------------------------------------
paso "Comprobaciones"
responde() { curl -sf -o /dev/null --max-time 5 "$1"; }
esperar() {   # esperar URL segundos
    for _ in $(seq 1 "$2"); do responde "$1" && return 0; sleep 1; done
    return 1
}
PORTAL="http://127.0.0.1:${PUERTO_FRONTEND:-8020}"
esperar "$PORTAL/api/salud" 90 && bien "Portal: $PORTAL" || aviso "El portal no responde en $PORTAL"
esperar "http://127.0.0.1:${PUERTO_CHATBOT:-8010}" 60 && bien "Chatbot local (Ollama): http://127.0.0.1:${PUERTO_CHATBOT:-8010}" \
    || aviso "El chatbot local no responde todavía"
esperar "http://127.0.0.1:${PUERTO_CHATBOT_RAG:-8011}" 60 && bien "Chatbot RAG: http://127.0.0.1:${PUERTO_CHATBOT_RAG:-8011}" \
    || aviso "El chatbot RAG no responde todavía"
esperar "http://127.0.0.1:${PUERTO_AIRFLOW:-8085}/api/v2/monitor/health" 120 \
    && bien "Airflow: http://127.0.0.1:${PUERTO_AIRFLOW:-8085}" || aviso "Airflow aún no responde (tarda en arrancar)"
esperar "http://127.0.0.1:${PUERTO_GRAFANA:-3000}/api/health" 60 \
    && bien "Grafana: http://127.0.0.1:${PUERTO_GRAFANA:-3000}" || aviso "Grafana no responde"

if "${COMPOSE[@]}" --profile chatbot exec -T ollama ollama list 2>/dev/null | grep -q "${OLLAMA_MODELO:-llama3.1:8b}"; then
    bien "Modelo de Ollama descargado (${OLLAMA_MODELO:-llama3.1:8b})"
else
    aviso "Ollama aún no tiene el modelo ${OLLAMA_MODELO:-llama3.1:8b} (se descarga solo la primera vez; tarda)"
fi

# La clave del LLM externo (chatbot RAG): se comprueba contra el proveedor sin mostrarla
if [[ -z "${LLM_API_KEY:-}" ]]; then
    aviso "Falta LLM_API_KEY: el chatbot RAG no funcionará. Pega una con 'make rag-clave'"
else
    codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
        -H "Authorization: Bearer ${LLM_API_KEY}" "${LLM_BASE_URL:-https://api.helmcode.com/v1}/models")
    case "$codigo" in
        200) bien "Clave del LLM externo aceptada (chatbot RAG operativo)" ;;
        401|403) aviso "El proveedor RECHAZA la clave del LLM (HTTP $codigo): caducada o revocada. Pega una nueva con 'make rag-clave'" ;;
        000) aviso "Sin respuesta del proveedor del LLM (¿sin internet?): el chatbot RAG no funcionará" ;;
        *) aviso "El proveedor del LLM responde HTTP $codigo: el chatbot RAG puede fallar" ;;
    esac
fi

echo
if [[ "$AVISOS" == 0 ]]; then
    echo "${verde}Todo listo.${fin} Portal en $PORTAL"
else
    echo "${ambar}Plataforma en marcha con $AVISOS aviso(s)${fin} (arriba). Portal en $PORTAL"
fi
echo "${gris}Para apagarla: make parar (conserva los datos). No uses Ctrl+C sobre un 'docker compose up': para el núcleo.${fin}"
