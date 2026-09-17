#!/bin/bash
# Envía un trabajo del proyecto al clúster en modo cluster (el driver corre en un worker).
# Uso (dentro del contenedor spark-master):
#   /opt/pids/lanzar.sh TiempoReal                       # streaming, supervisado: se reinicia si cae
#   /opt/pids/lanzar.sh CargaHistorica s3a://crudo/... lote
set -euo pipefail
clase=${1:?Uso: lanzar.sh <TiempoReal|CargaHistorica> [argumentos]}
shift

supervisar=()
if [[ "$clase" == "TiempoReal" ]]; then
    supervisar=(--supervise)
fi

exec /opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode cluster \
    "${supervisar[@]}" \
    --class "pids.$clase" \
    --name "pids-${clase,,}" \
    --conf spark.cores.max="${PIDS_CORES:-3}" \
    --conf spark.executor.cores=1 \
    --conf spark.executor.memory="${PIDS_MEMORIA_EJECUTOR:-1g}" \
    --conf spark.driver.memory=1g \
    --conf spark.standalone.submit.waitAppCompletion=false \
    file:/opt/pids/pids-spark.jar "$@"
