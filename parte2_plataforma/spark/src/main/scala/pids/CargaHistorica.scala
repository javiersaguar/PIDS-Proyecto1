package pids

import org.apache.spark.sql.functions._
import org.apache.spark.sql.{DataFrame, SparkSession}

import java.sql.Timestamp
import java.time.Instant

/** Carga histórica (lotes): fichero de viajes en S3 -> validación -> zona restringida -> agregados protegidos.
  *
  * Uso: spark-submit --deploy-mode cluster --class pids.CargaHistorica pids-spark.jar <entrada> [lote]
  *   entrada  s3a://crudo/historico/yellow_tripdata_2020-01.parquet (o .csv)
  */
object CargaHistorica {

  final case class Resumen(
      lote: String,
      entrada: String,
      origen: String,
      filas: Long,
      validos: Long,
      rechazados: Long,
      motivos: Map[String, Long],
      grupos_publicados: Map[String, Long],
      grupos_suprimidos: Map[String, Long],
      version_reglas: Int,
      instante: Timestamp)

  def main(args: Array[String]): Unit = {
    require(args.nonEmpty, "Uso: CargaHistorica <entrada s3a://...> [lote]")
    val entrada = args(0)
    val lote = args.lift(1).getOrElse(entrada.split('/').last)
    val spark = Sesion.crear(s"pids-carga-historica-$lote")
    try {
      val zonas = Referencia.zonas(spark).cache()
      Publicacion.mongo(Referencia.publicable(zonas), "publico", "zonas")
      val resumen = ejecutar(spark, Config.cargar(), entrada, lote, zonas, Publicacion.mongo, Rutas.crudo)
      import spark.implicits._
      Publicacion.mongoInsertar(Seq(resumen).toDF(), "auditoria", "cargas")
      println(s"[pids] carga $lote: ${resumen.validos} válidos, ${resumen.rechazados} rechazados, " +
        s"grupos publicados ${resumen.grupos_publicados}, suprimidos ${resumen.grupos_suprimidos}")
    } finally spark.stop()
  }

  def leer(spark: SparkSession, entrada: String): DataFrame =
    if (entrada.endsWith(".parquet") || !entrada.contains(".")) spark.read.parquet(entrada)
    else spark.read.option("header", "true").csv(entrada)

  /** Toda la lógica, sin efectos fijos: los tests pasan su propio publicador y un directorio temporal. */
  def ejecutar(spark: SparkSession, cfg: Config, entrada: String, lote: String, zonas: DataFrame,
               publicar: Publicacion.Publicador, destinoCrudo: String): Resumen = {
    val validado = Esquema.validar(Esquema.normalizar(leer(spark, entrada), cfg.esquema), cfg.esquema)
      .withColumn("origen", lit("historico"))
      .withColumn("lote", lit(lote))
      .persist()
    val (validos, rechazados) = Esquema.separar(validado, cfg.esquema)

    // zona restringida: solo Spark y la ingesta tienen credenciales para este bucket
    validos.write.mode("overwrite").parquet(s"$destinoCrudo/validos/historico/lote=$lote")
    rechazados.write.mode("overwrite").json(s"$destinoCrudo/rechazos/historico/lote=$lote")

    val conZonas = Privacidad.conZonas(validos, zonas).persist()
    val grupos = cfg.privacidad.niveles.keys.toSeq.sorted.map { nivel =>
      val doc = Privacidad.publicable(Privacidad.agregar(conZonas, nivel), nivel, cfg.privacidad).persist()
      publicar(doc, "publico", cfg.privacidad.coleccion(nivel, "historico"))
      val total = doc.count()
      val suprimidos = doc.filter(col("suprimido")).count()
      doc.unpersist()
      (nivel, total, suprimidos)
    }

    val motivos = rechazados.select(explode(col(Esquema.Motivos)).as("m")).groupBy("m").count()
      .collect().map(r => r.getString(0) -> r.getLong(1)).toMap
    val resumen = Resumen(
      lote = lote,
      entrada = entrada,
      origen = "historico",
      filas = validado.count(),
      validos = validos.count(),
      rechazados = rechazados.count(),
      motivos = motivos,
      grupos_publicados = grupos.map(g => g._1 -> g._2).toMap,
      grupos_suprimidos = grupos.map(g => g._1 -> g._3).toMap,
      version_reglas = cfg.privacidad.version,
      instante = Timestamp.from(Instant.now()))
    conZonas.unpersist()
    validado.unpersist()
    resumen
  }
}
