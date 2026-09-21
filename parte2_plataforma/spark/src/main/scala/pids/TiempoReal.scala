package pids

import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.Trigger
import org.apache.spark.sql.types.{MapType, StringType, StructType}
import org.apache.spark.sql.DataFrame

/** Tiempo real (Structured Streaming): topic viajes-crudos -> misma validación y mismas reglas de
  * privacidad que el histórico -> zona restringida + agregados protegidos (colecciones tr_*).
  *
  * Se lanza una vez y queda supervisado por el máster (spark-submit --deploy-mode cluster --supervise).
  */
object TiempoReal {

  /** Los eventos de la API de captura: {"registro": {...campos del proveedor...}, "origen", "lote", ...}. */
  private val esquemaEvento = new StructType()
    .add("registro", MapType(StringType, StringType))
    .add("origen", StringType)
    .add("lote", StringType)

  /** Convierte el evento en una fila con las columnas de la fuente (en minúsculas), como un CSV. */
  def desenvolver(eventos: DataFrame, cfg: ConfigEsquema): DataFrame = {
    val e = eventos.select(from_json(col("value").cast("string"), esquemaEvento).as("e"))
    val registro = transform_keys(col("e.registro"), (k, _) => lower(trim(k)))
    e.select(cfg.alias.map { case (fuente, _) => element_at(registro, lit(fuente)).as(fuente) } :+
      coalesce(col("e.lote"), lit("sin_lote")).as("lote"): _*)
  }

  def main(args: Array[String]): Unit = {
    val spark = Sesion.crear("pids-tiempo-real")
    val cfg = Config.cargar()
    val zonas = Referencia.zonas(spark).cache()

    val eventos = spark.readStream.format("kafka")
      .option("kafka.bootstrap.servers", Rutas.brokers)
      .option("subscribe", Rutas.topicViajes)
      .option("startingOffsets", "earliest")
      .option("failOnDataLoss", "false")
      .load()

    val validado = Esquema.validar(
      Esquema.normalizar(desenvolver(eventos, cfg.esquema), cfg.esquema, conservar = Seq("lote")),
      cfg.esquema).withColumn("origen", lit("tiempo_real"))

    // 1) archivo en la zona restringida
    val archivar: (DataFrame, Long) => Unit = (lote, _) => {
      val (validos, rechazados) = Esquema.separar(lote, cfg.esquema)
      validos.write.mode("append").parquet(s"${Rutas.crudo}/validos/tiempo_real")
      rechazados.write.mode("append").json(s"${Rutas.crudo}/rechazos/tiempo_real")
    }
    validado.writeStream
      .queryName("archivo_zona_restringida")
      .option("checkpointLocation", s"${Rutas.checkpoints}/archivo")
      .trigger(Trigger.ProcessingTime("10 seconds"))
      .foreachBatch(archivar)
      .start()

    // 2) agregados protegidos, uno por nivel.
    // Sin supresión complementaria: necesita el día completo y aquí cada micro-lote trae solo los grupos
    // que cambian (además, Spark no admite ventanas por partición en streaming). Riesgo documentado en
    // docs/escenario_E3.md.
    val validos = Esquema.tipar(validado.filter(size(col(Esquema.Motivos)) === 0).drop(Esquema.Motivos), cfg.esquema)
      .withWatermark("recogida", "2 hours")
    val conZonas = Privacidad.conZonas(validos, zonas)
    cfg.privacidad.niveles.keys.toSeq.sorted.foreach { nivel =>
      val coleccion = cfg.privacidad.coleccion(nivel, "tiempo_real")
      val publicar: (DataFrame, Long) => Unit = (agregado, _) =>
        Publicacion.mongo(Privacidad.publicable(agregado, nivel, cfg.privacidad), "publico", coleccion)
      Privacidad.agregar(conZonas, nivel).writeStream
        .queryName(s"agregados_$nivel")
        .outputMode("update")
        .option("checkpointLocation", s"${Rutas.checkpoints}/$nivel")
        .trigger(Trigger.ProcessingTime("30 seconds"))
        .foreachBatch(publicar)
        .start()
    }

    spark.streams.awaitAnyTermination()
  }
}
