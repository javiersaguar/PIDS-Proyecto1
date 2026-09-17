# Imagen del clúster Spark (máster y workers) con los trabajos del proyecto ya compilados.
# Contexto de construcción: la raíz del repositorio.

# --- Etapa 1: compilar los trabajos Scala y reunir las dependencias de los conectores ---
FROM sbtscala/scala-sbt:eclipse-temurin-17.0.20_8_1.13.0_2.13.18 AS compilacion
USER root
WORKDIR /build/parte2_plataforma/spark
ENV SBT_OPTS="-Dsbt.supershell=false -Dsbt.color=false"

COPY parte2_plataforma/spark/build.sbt ./
COPY parte2_plataforma/spark/project/build.properties ./project/
RUN sbt update

COPY config /build/config
COPY data/muestra /build/data/muestra
COPY parte2_plataforma/spark/src ./src

# make test-spark construye solo esta etapa con EJECUTAR_TESTS=true
ARG EJECUTAR_TESTS=false
RUN if [ "$EJECUTAR_TESTS" = "true" ]; then sbt test; fi

RUN sbt package \
 && mkdir -p /build/dependencias \
 && sbt --error "export Runtime / dependencyClasspath" | tail -n 1 | tr ':' '\n' | grep '\.jar$' \
    | xargs -I{} cp {} /build/dependencias/

# --- Etapa 2: Spark oficial + conectores + trabajos ---
FROM apache/spark:4.0.4-scala2.13-java17-ubuntu
USER root

COPY --from=compilacion /build/dependencias /tmp/dependencias
COPY parte2_plataforma/spark/instalar_dependencias.sh /tmp/
RUN bash /tmp/instalar_dependencias.sh /tmp/dependencias /opt/spark/jars \
 && rm -rf /tmp/dependencias /tmp/instalar_dependencias.sh

COPY --from=compilacion /build/parte2_plataforma/spark/target/scala-2.13/pids-spark_2.13-0.1.0.jar /opt/pids/pids-spark.jar
COPY config /opt/pids/config
COPY parte2_plataforma/spark/conf/ /opt/spark/conf/
COPY parte2_plataforma/spark/lanzar.sh /opt/pids/lanzar.sh

RUN mkdir -p /opt/spark/work /opt/spark/logs /opt/spark/checkpoints \
 && chown -R spark:spark /opt/spark/work /opt/spark/logs /opt/spark/checkpoints \
 && chmod +x /opt/pids/lanzar.sh

ENV PIDS_CONFIG_DIR=/opt/pids/config
USER spark
WORKDIR /opt/spark
