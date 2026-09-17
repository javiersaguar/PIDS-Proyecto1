// Trabajos Spark de la plataforma (Scala). Se compila dentro de la imagen Docker (ver Dockerfile),
// así que no hace falta instalar sbt ni Java en el equipo.

ThisBuild / scalaVersion := "2.13.16"   // la misma que trae Spark 4.0.4
ThisBuild / organization := "es.upm.pids"

val versionSpark = "4.0.4"

lazy val root = (project in file("."))
  .settings(
    name := "pids-spark",
    version := "0.1.0",
    libraryDependencies ++= Seq(
      // Spark ya está en el clúster: solo para compilar
      "org.apache.spark" %% "spark-sql" % versionSpark % Provided,
      // Conectores: se copian a /opt/spark/jars de la imagen
      "org.apache.spark" %% "spark-sql-kafka-0-10" % versionSpark,
      "org.mongodb.spark" %% "mongo-spark-connector" % "11.1.0",
      "org.apache.hadoop" % "hadoop-aws" % "3.4.1",   // S3A; la versión de Hadoop de Spark 4.0.4
      "org.scalatest" %% "scalatest" % "3.2.19" % Test
    ),
    scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked"),
    Test / fork := true,
    Test / envVars := Map("PIDS_CONFIG_DIR" -> sys.env.getOrElse("PIDS_CONFIG_DIR", "../../config")),
    // Spark 4 en Java 17 necesita abrir estos módulos (spark-submit lo hace solo; los tests no)
    Test / javaOptions ++= Seq(
      "-Xmx2g",
      "-XX:+IgnoreUnrecognizedVMOptions",
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
      "--add-opens=java.base/java.io=ALL-UNNAMED",
      "--add-opens=java.base/java.net=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED",
      "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED",
      "--add-opens=java.base/jdk.internal.ref=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED",
      "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
      "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED",
      "-Djdk.reflect.useDirectMethodHandle=false",
      "-Dio.netty.tryReflectionSetAccessible=true"
    )
  )
