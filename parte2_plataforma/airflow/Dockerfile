# Airflow con el cliente de Spark, para enviar trabajos al clúster en modo cluster.
FROM apache/airflow:3.3.2-python3.12

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless \
 && rm -rf /var/lib/apt/lists/*
# Solo hace falta spark-submit: se copia la distribución de la imagen oficial (misma versión que el clúster)
COPY --from=apache/spark:4.0.4-scala2.13-java17-ubuntu /opt/spark /opt/spark
# En modo cluster, el driver recibe la configuración del CLIENTE: sin esto saldría sin el endpoint de
# S3 ni la pasarela REST del máster (fallaría con 403 al leer los datos).
COPY parte2_plataforma/spark/conf/ /opt/spark/conf/
ENV SPARK_HOME=/opt/spark \
    JAVA_HOME=/usr/lib/jvm/default-java \
    PATH="${PATH}:/opt/spark/bin"

USER airflow
RUN pip install --no-cache-dir "apache-airflow==3.3.2" "apache-airflow-providers-apache-spark==6.3.2"
