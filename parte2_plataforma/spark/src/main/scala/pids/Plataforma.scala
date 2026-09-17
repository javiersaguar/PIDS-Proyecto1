package pids

import org.apache.spark.sql.functions._
import org.apache.spark.sql.{DataFrame, SparkSession}

/** Rutas y conexiones. Todo se configura por variables de entorno de los contenedores de Spark,
  * para que ningún secreto aparezca en los argumentos de spark-submit ni en la interfaz de Spark. */
object Rutas {
  val crudo: String = sys.env.getOrElse("PIDS_S3_CRUDO", "s3a://crudo")
  val zonas: String = sys.env.getOrElse("PIDS_ZONAS", "s3a://referencia/taxi_zone_lookup.csv")
  val brokers: String = sys.env.getOrElse("PIDS_KAFKA_BROKERS", "redpanda:9092")
  val topicViajes: String = sys.env.getOrElse("PIDS_TOPIC_VIAJES", "viajes-crudos")
  val checkpoints: String = sys.env.getOrElse("PIDS_CHECKPOINTS", "/opt/spark/checkpoints/tiempo_real")
  def mongo: String = sys.env.getOrElse("PIDS_MONGO_URI", throw new IllegalStateException("Falta PIDS_MONGO_URI"))
}

object Sesion {
  def crear(nombre: String): SparkSession =
    SparkSession.builder().appName(nombre).config("spark.sql.session.timeZone", "UTC").getOrCreate()
}

object Referencia {
  /** Tabla pública de zonas de la TLC (LocationID, Borough, Zone, service_zone). */
  def zonas(spark: SparkSession, ruta: String = Rutas.zonas): DataFrame =
    spark.read.option("header", "true").csv(ruta)

  /** Versión publicable de la tabla de zonas (dato de referencia, no personal). */
  def publicable(zonas: DataFrame): DataFrame = zonas.select(
    col("LocationID").cast("int").as("_id"),
    col("Zone").as("nombre"),
    col("Borough").as("barrio"),
    col("service_zone").as("tipo_servicio"))
}

object Publicacion {
  type Publicador = (DataFrame, String, String) => Unit   // (datos, base de datos, colección)

  /** Reemplaza por _id: reprocesar un lote no duplica agregados. */
  val mongo: Publicador = (df, base, coleccion) =>
    df.write.format("mongodb").mode("append")
      .option("connection.uri", Rutas.mongo)
      .option("database", base)
      .option("collection", coleccion)
      .option("operationType", "replace")
      .option("idFieldList", "_id")
      .option("upsertDocument", "true")
      .save()

  /** Solo inserta (la colección de auditoría no admite otra cosa). */
  val mongoInsertar: Publicador = (df, base, coleccion) =>
    df.write.format("mongodb").mode("append")
      .option("connection.uri", Rutas.mongo)
      .option("database", base)
      .option("collection", coleccion)
      .option("operationType", "insert")
      .save()
}
