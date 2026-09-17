#!/bin/sh
# Arranca SeaweedFS (máster + volumen + filer + pasarela S3) con las identidades de s3.plantilla.json.
# Las claves llegan por variables de entorno y se sustituyen aquí: no se guardan en el repositorio.
set -eu

plantilla=/etc/pids/s3.plantilla.json
config=/tmp/s3.json
cp "$plantilla" "$config"
for var in S3_ADMIN_ACCESS_KEY S3_ADMIN_SECRET_KEY S3_SPARK_ACCESS_KEY S3_SPARK_SECRET_KEY \
           S3_INGESTA_ACCESS_KEY S3_INGESTA_SECRET_KEY; do
    valor=$(printenv "$var" || true)
    [ -n "$valor" ] || { echo "Falta la variable $var" >&2; exit 1; }
    sed -i "s|\${$var}|$valor|g" "$config"
done
chmod 600 "$config"

exec weed server \
    -dir=/data \
    -master.volumeSizeLimitMB=1024 \
    -volume.max=0 \
    -s3 \
    -s3.port=8333 \
    -s3.config="$config" \
    -metricsPort=9327
