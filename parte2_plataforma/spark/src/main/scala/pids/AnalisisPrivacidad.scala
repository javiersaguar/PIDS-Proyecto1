package pids

import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.hadoop.fs.Path
import org.apache.spark.sql.functions._
import org.apache.spark.sql.{DataFrame, SparkSession}

import java.nio.charset.StandardCharsets
import java.time.Instant
import scala.jdk.CollectionConverters._

/** Curva privacidad-utilidad: cuánto se suprime y cuánto se sigue publicando con cada umbral k.
  *
  * Lee los viajes válidos de la zona restringida, agrega como la carga histórica y, para cada nivel y
  * cada k, cuenta grupos, grupos suprimidos y viajes que quedan en grupos publicados; con y sin la
  * supresión complementaria. NO publica nada en MongoDB ni cambia config/privacidad.json: solo cuenta.
  * Las cifras de salida son agregadas; ningún viaje individual sale de Spark.
  *
  * Uso: spark-submit --deploy-mode cluster --class pids.AnalisisPrivacidad pids-spark.jar \
  *        [entrada] [salida.json] [k1,k2,...]
  *   entrada  por defecto s3a://crudo/validos/historico/lote=anio-2020
  *   salida   por defecto s3a://crudo/informes/curva_privacidad.json (un único fichero JSON)
  */
object AnalisisPrivacidad {

  val UmbralesPorDefecto: Seq[Int] = Seq(5, 10, 20, 50)

  final case class Punto(
      nivel: String,
      k: Int,
      grupos: Long,
      suprimidos: Long,                   // solo por el umbral k
      suprimidosConComplementaria: Long,  // umbral k + supresión complementaria
      viajes: Long,
      viajesPublicados: Long,
      viajesPublicadosConComplementaria: Long) {
    def pct(parte: Long, total: Long): Double = if (total == 0) 0.0 else math.round(1000.0 * parte / total) / 10.0
    def pctGruposSuprimidos: Double = pct(suprimidos, grupos)
    def pctViajesPublicados: Double = pct(viajesPublicados, viajes)
    def pctViajesPublicadosConComplementaria: Double = pct(viajesPublicadosConComplementaria, viajes)
  }

  /** Un punto de la curva por nivel y umbral. Agrega una vez por nivel y aplica cada k sobre los
    * agregados, con las mismas supresiones complementarias que la carga histórica. */
  def curva(conZonas: DataFrame, niveles: Seq[String], umbrales: Seq[Int]): Seq[Punto] = {
    val agregados = niveles.map(n => n -> Privacidad.agregar(conZonas, n).persist()).toMap
    def contar(condicion: String) = sum(when(col(condicion), 1L).otherwise(0L))
    def publicados(condicion: String) = sum(when(!col(condicion), col("n_viajes")).otherwise(0L))
    val puntos = umbrales.flatMap { k =>
      val marcados = Privacidad.suprimirComplementariosTodos(agregados, k)
      niveles.map { nivel =>
        val r = marcados(nivel)
          .withColumn("_sup", col("n_viajes") < k)
          .withColumn("_sup_c", col("_sup") || col("complementario"))
          .agg(count(lit(1)), contar("_sup"), contar("_sup_c"), sum("n_viajes"), publicados("_sup"),
            publicados("_sup_c"))
          .collect().head
        Punto(nivel, k, r.getLong(0), r.getLong(1), r.getLong(2), r.getLong(3), r.getLong(4), r.getLong(5))
      }
    }
    agregados.values.foreach(_.unpersist())
    puntos.sortBy(p => (p.nivel, p.k))
  }

  def tabla(puntos: Seq[Punto]): String = {
    val cabecera = Seq(
      "| nivel | k | grupos | suprimidos | % suprimidos | viajes publicados | % viajes publicados | suprimidos con complementaria | % viajes publicados con complementaria |",
      "|---|---|---|---|---|---|---|---|---|")
    val filas = puntos.map { p =>
      s"| ${p.nivel} | ${p.k} | ${p.grupos} | ${p.suprimidos} | ${p.pctGruposSuprimidos} | ${p.viajesPublicados} | " +
        s"${p.pctViajesPublicados} | ${p.suprimidosConComplementaria} | ${p.pctViajesPublicadosConComplementaria} |"
    }
    (cabecera ++ filas).mkString("\n")
  }

  def json(entrada: String, puntos: Seq[Punto]): String = {
    val filas = puntos.map { p =>
      Map[String, Any](
        "nivel" -> p.nivel, "k" -> p.k, "grupos" -> p.grupos, "suprimidos" -> p.suprimidos,
        "suprimidos_con_complementaria" -> p.suprimidosConComplementaria, "viajes" -> p.viajes,
        "viajes_publicados" -> p.viajesPublicados,
        "viajes_publicados_con_complementaria" -> p.viajesPublicadosConComplementaria,
        "pct_grupos_suprimidos" -> p.pctGruposSuprimidos, "pct_viajes_publicados" -> p.pctViajesPublicados,
        "pct_viajes_publicados_con_complementaria" -> p.pctViajesPublicadosConComplementaria
      ).asJava
    }.asJava
    val documento = Map[String, Any]("generado" -> Instant.now().toString, "entrada" -> entrada,
      "curva" -> filas).asJava
    new ObjectMapper().writerWithDefaultPrettyPrinter().writeValueAsString(documento)
  }

  /** Un único fichero (no el directorio de partes que escribe Spark), para leerlo cómodamente. */
  def escribir(spark: SparkSession, ruta: String, contenido: String): Unit = {
    val destino = new Path(ruta)
    val fs = destino.getFileSystem(spark.sparkContext.hadoopConfiguration)
    val salida = fs.create(destino, true)
    try salida.write(contenido.getBytes(StandardCharsets.UTF_8)) finally salida.close()
  }

  def main(args: Array[String]): Unit = {
    val entrada = args.lift(0).getOrElse(s"${Rutas.crudo}/validos/historico/lote=anio-2020")
    val salida = args.lift(1).getOrElse(s"${Rutas.crudo}/informes/curva_privacidad.json")
    val umbrales = args.lift(2).map(_.split(',').map(_.trim.toInt).toSeq).getOrElse(UmbralesPorDefecto)
    val spark = Sesion.crear("pids-analisis-privacidad")
    try {
      val cfg = Config.cargar()
      val conZonas = Privacidad.conZonas(spark.read.parquet(entrada), Referencia.zonas(spark)).persist()
      val puntos = curva(conZonas, cfg.privacidad.niveles.keys.toSeq.sorted, umbrales)
      println(s"[pids] curva privacidad-utilidad de $entrada\n${tabla(puntos)}")
      escribir(spark, salida, json(entrada, puntos))
      println(s"[pids] curva guardada en $salida")
    } finally spark.stop()
  }
}
