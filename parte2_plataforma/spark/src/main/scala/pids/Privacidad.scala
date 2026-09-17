package pids

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.{DoubleType, LongType}
import org.apache.spark.sql.{Column, DataFrame}

/** Reglas propias de privacidad al publicar (E3).
  *
  *  - Solo salen agregados, nunca viajes: por hora y zona de origen, por día y barrio, y flujos
  *    entre barrios por día. El destino no se publica a nivel de hora ni de zona.
  *  - Los grupos con menos de `k_minimo` viajes se publican marcados como `suprimido`, sin cifras.
  *  - Las medias se redondean.
  *
  * Las mismas funciones sirven para lotes y para streaming (las ventanas de `window` funcionan en
  * los dos modos).
  */
object Privacidad {

  private def metricas: Seq[Column] = Seq(
    count(lit(1)).as("n_viajes"),
    avg("distancia_millas").as("distancia_media"),
    avg("importe_total").as("importe_medio"),
    avg("propina").as("propina_media"),
    avg(when(col("tipo_pago") === 1, 100.0).otherwise(0.0)).as("pct_pago_tarjeta")
  )

  /** Añade barrio y nombre de zona con la tabla pública de zonas de la TLC. */
  def conZonas(viajes: DataFrame, zonas: DataFrame): DataFrame = {
    val origen = zonas.select(
      col("LocationID").cast("int").as("zona_origen"),
      col("Borough").as("barrio_origen"),
      col("Zone").as("zona_origen_nombre"))
    val destino = zonas.select(col("LocationID").cast("int").as("zona_destino"), col("Borough").as("barrio_destino"))
    viajes
      .join(broadcast(origen), Seq("zona_origen"), "left")
      .join(broadcast(destino), Seq("zona_destino"), "left")
  }

  /** Agregado de un nivel (sin proteger todavía). */
  def agregar(viajes: DataFrame, nivel: String): DataFrame = {
    val (ventana, dims) = nivel match {
      case "hora_zona"     => ("1 hour", Seq("zona_origen", "zona_origen_nombre", "barrio_origen"))
      case "dia_barrio"    => ("1 day", Seq("barrio_origen"))
      case "od_dia_barrio" => ("1 day", Seq("barrio_origen", "barrio_destino"))
      case otro            => throw new IllegalArgumentException(s"nivel desconocido: $otro")
    }
    val agrupado = viajes
      .groupBy((window(col("recogida"), ventana).as("ventana") +: dims.map(col)): _*)
      .agg(metricas.head, metricas.tail: _*)
    if (ventana == "1 hour") agrupado.withColumn("hora", col("ventana.start")).drop("ventana")
    else agrupado.withColumn("dia", to_date(col("ventana.start"))).drop("ventana")
  }

  /** Suprime los grupos pequeños y redondea. */
  def proteger(agregado: DataFrame, cfg: ConfigPrivacidad): DataFrame = {
    val conMarca = agregado.withColumn("suprimido", col("n_viajes") < cfg.kMinimo)
    cfg.metricas.filterNot(_ == "n_viajes")
      .foldLeft(conMarca) { (d, m) =>
        d.withColumn(m, when(col("suprimido"), lit(null).cast(DoubleType)).otherwise(round(col(m), cfg.decimales)))
      }
      .withColumn("n_viajes", when(col("suprimido"), lit(null).cast(LongType)).otherwise(col("n_viajes")))
  }

  /** Documento listo para MongoDB: protegido, con _id estable (para reemplazar al reprocesar) y versión de las reglas. */
  def publicable(agregado: DataFrame, nivel: String, cfg: ConfigPrivacidad): DataFrame = {
    val dims = cfg.niveles(nivel).dimensiones
    proteger(agregado, cfg)
      .withColumn("_id", concat_ws("|", dims.map(d => coalesce(col(d).cast("string"), lit("desconocido"))): _*))
      .withColumn("nivel", lit(nivel))
      .withColumn("version_reglas", lit(cfg.version))
      .withColumn("actualizado_en", current_timestamp())
  }
}
