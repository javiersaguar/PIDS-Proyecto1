package pids

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.sql.{Column, DataFrame}

/** Esquema canónico y validación de viajes (versión Spark de parte2_plataforma/comun/esquema.py).
  *
  * La misma función sirve para el histórico (CSV/Parquet) y para los eventos en tiempo real: es la
  * garantía de que los dos caminos aplican exactamente las mismas reglas (E3).
  *
  * Semántica de nulos (igual que en Python): un campo vacío solo invalida el viaje si es obligatorio.
  */
object Esquema {
  val Motivos = "motivos"

  /** Renombra al esquema canónico y convierte tipos. Los valores no convertibles quedan como nulos.
    * Los códigos numéricos se dejan como Double hasta validar (ver `tipar`).
    *
    * @param conservar columnas de la fuente que se mantienen tal cual (procedencia, por ejemplo)
    */
  def normalizar(df: DataFrame, cfg: ConfigEsquema, conservar: Seq[String] = Nil): DataFrame = {
    val porNombre = df.schema.fields.map(f => f.name.trim.toLowerCase -> f).toMap
    val columnas = cfg.alias.map { case (fuente, canon) =>
      porNombre.get(fuente) match {
        case None    => lit(null).cast(tipoDestino(canon, cfg)).as(canon)
        case Some(f) => convertir(f, canon, cfg).as(canon)
      }
    }
    df.select(columnas ++ conservar.map(c => col(s"`$c`")): _*)
  }

  private def tipoDestino(canon: String, cfg: ConfigEsquema): DataType =
    if (cfg.fechas(canon)) TimestampType else if (cfg.texto(canon)) StringType else DoubleType

  private def convertir(f: StructField, canon: String, cfg: ConfigEsquema): Column = {
    val c = col(s"`${f.name}`")
    val n = s"`${f.name}`"
    if (cfg.fechas(canon)) f.dataType match {
      case TimestampType | TimestampNTZType | DateType => c.cast(TimestampType)
      case _ =>
        // cada fuente trae su formato: muestra de Moodle, exportación completa (mes abreviado) o ISO
        val intentos = cfg.formatosFecha.map(fmt => s"try_to_timestamp(trim($n), '$fmt')") :+
          s"try_to_timestamp(trim($n))"
        expr(intentos.mkString("coalesce(", ", ", ")"))
    }
    else if (cfg.texto(canon)) upper(trim(c.cast(StringType)))
    else f.dataType match {
      case _: NumericType => c.cast(DoubleType)
      case _ if cfg.decimalComa =>
        // "1,2" y "1.234,56": con coma decimal, el punto es separador de miles
        expr(s"""case when trim($n) like '%,%'
                 |     then try_cast(replace(replace(trim($n), '.', ''), ',', '.') AS DOUBLE)
                 |     else try_cast(trim($n) AS DOUBLE) end""".stripMargin)
      case _ => expr(s"try_cast(trim($n) AS DOUBLE)")
    }
  }

  /** Añade la columna `motivos` con las reglas incumplidas (vacía si el viaje es válido). */
  def validar(df: DataFrame, cfg: ConfigEsquema): DataFrame = {
    val duracion = expr("unix_seconds(llegada) - unix_seconds(recogida)")
    def fueraDeLista[T](c: String, validos: Seq[T]): Column = not(col(c).isin(validos: _*))
    def zonaInvalida(c: String): Column =
      col(c) < cfg.zonaMinima || col(c) > cfg.zonaMaxima || col(c) =!= floor(col(c))

    val reglas: Seq[(String, Column)] = Seq(
      "falta_campo_obligatorio" -> cfg.obligatorias.map(c => col(c).isNull).reduce(_ || _),
      "fecha_fuera_de_rango" -> (col("recogida") < to_timestamp(lit(cfg.recogidaDesde)) ||
        col("recogida") >= to_timestamp(lit(cfg.recogidaHasta))),
      "duracion_no_positiva" -> (duracion <= 0),
      "duracion_excesiva" -> (duracion > cfg.duracionMaximaHoras * 3600),
      "distancia_fuera_de_rango" -> (col("distancia_millas") < 0 || col("distancia_millas") > cfg.distanciaMaxima),
      "importe_negativo" -> (col("tarifa") < 0 || col("importe_total") < 0),
      "vendor_desconocido" -> fueraDeLista("vendor_id", cfg.vendors),
      "zona_desconocida" -> (zonaInvalida("zona_origen") || zonaInvalida("zona_destino")),
      "tipo_pago_desconocido" -> fueraDeLista("tipo_pago", cfg.tiposPago),
      "tarifa_desconocida" -> fueraDeLista("tarifa_id", cfg.tarifas),
      "indicador_invalido" -> fueraDeLista("almacenado_y_reenviado", cfg.indicadores)
    )
    val motivos = array_compact(array(reglas.map { case (nombre, incumple) =>
      when(coalesce(incumple, lit(false)), lit(nombre))
    }: _*))
    df.withColumn(Motivos, motivos)
  }

  /** Tipos definitivos para guardar: los códigos pasan a entero (ya validados). */
  def tipar(df: DataFrame, cfg: ConfigEsquema): DataFrame =
    cfg.enteras.foldLeft(df)((d, c) => d.withColumn(c, col(c).cast(IntegerType)))

  /** Separa (válidos, rechazados) a partir de la columna `motivos`. */
  def separar(validado: DataFrame, cfg: ConfigEsquema): (DataFrame, DataFrame) = {
    val validos = tipar(validado.filter(size(col(Motivos)) === 0).drop(Motivos), cfg)
    val rechazados = validado.filter(size(col(Motivos)) > 0)
    (validos, rechazados)
  }
}
