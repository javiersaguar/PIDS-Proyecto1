#!/bin/bash
# Copia a Spark las librerías de los conectores (Kafka, MongoDB, S3A) que Spark no trae ya.
# Si Spark ya incluye una librería (slf4j, snappy, zstd...), se deja la suya para no tener dos
# versiones de la misma clase en el classpath.
# Uso: instalar_dependencias.sh <carpeta con jars> <carpeta jars de Spark>
set -euo pipefail
origen=$1
destino=$2

base() { basename "$1" .jar | sed -E 's/-[0-9][0-9A-Za-z.+_-]*$//'; }

declare -A incluidas
for jar in "$destino"/*.jar; do
    incluidas[$(base "$jar")]=1
done

for jar in "$origen"/*.jar; do
    nombre=$(base "$jar")
    if [[ -n "${incluidas[$nombre]:-}" ]]; then
        echo "  ya en Spark:  $(basename "$jar")"
    else
        cp "$jar" "$destino/"
        echo "  añadida:      $(basename "$jar")"
    fi
done
