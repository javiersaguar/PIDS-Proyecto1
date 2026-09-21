package pids

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.Files
import scala.collection.mutable

class AnalisisPrivacidadSpec extends AnyFunSuite with SparkLocal {
  import spark.implicits._

  private val k = 10

  /** Agregado de juguete del nivel od_dia_barrio: (barrio origen, barrio destino, viajes) en un día. */
  private def od(filas: (String, String, Long)*): DataFrame =
    filas.toDF("barrio_origen", "barrio_destino", "n_viajes")
      .withColumn("dia", lit(java.sql.Date.valueOf("2020-01-15")))

  private def complementarios(df: DataFrame, nivel: String): Set[String] =
    Privacidad.suprimirComplementarios(df, nivel, k).filter(col("complementario"))
      .select("barrio_destino").as[String].collect().toSet

  test("un único grupo suprimido obliga a suprimir el visible más pequeño") {
    val df = od(("Queens", "Bronx", 3), ("Queens", "Brooklyn", 12), ("Queens", "Manhattan", 15))
    assert(complementarios(df, "od_dia_barrio") == Set("Brooklyn"))
  }

  test("varios suprimidos cuya suma no los delata no necesitan complementario") {
    // 4 + 6 = 10 entre dos grupos: cada uno puede valer de 1 a 9
    val df = od(("Queens", "Bronx", 4), ("Queens", "EWR", 6), ("Queens", "Manhattan", 15))
    assert(complementarios(df, "od_dia_barrio").isEmpty)
  }

  test("suprimidos que suman lo mínimo (todos con un viaje) también se protegen") {
    val df = od(("Queens", "Bronx", 1), ("Queens", "EWR", 1), ("Queens", "Staten Island", 1),
      ("Queens", "Manhattan", 30), ("Queens", "Brooklyn", 12))
    assert(complementarios(df, "od_dia_barrio") == Set("Brooklyn"))
  }

  test("las particiones son independientes y sin visibles no hay complementario") {
    val df = od(("Queens", "Bronx", 3), ("Queens", "Manhattan", 15),
      ("Bronx", "Queens", 2), ("Bronx", "EWR", 5))
    val marcado = Privacidad.suprimirComplementarios(df, "od_dia_barrio", k)
      .filter(col("complementario")).select("barrio_origen", "barrio_destino").as[(String, String)].collect()
    assert(marcado.toSet == Set(("Queens", "Manhattan")))
  }

  /** Agregado de juguete del nivel hora_zona: (hora, zona, barrio, viajes). */
  private def hz(filas: (String, Int, String, Long)*): DataFrame =
    filas.map { case (h, z, b, n) => (java.sql.Timestamp.valueOf(s"2020-01-15 $h:00:00"), z, b, n) }
      .toDF("hora", "zona_origen", "barrio_origen", "n_viajes")

  private def db(filas: (String, Long)*): DataFrame =
    filas.toDF("barrio_origen", "n_viajes").withColumn("dia", lit(java.sql.Date.valueOf("2020-01-15")))

  test("si todos los grupos del día están suprimidos y se delatan, se oculta el total del día") {
    // once grupos de un viaje: el total (11) revelaría que cada uno tiene exactamente un viaje
    val horaZona = hz((0 until 11).map(h => (f"$h%02d", 23, "Staten Island", 1L)): _*)
    val expuestos = Privacidad.padresExpuestos(horaZona, "hora_zona", k)
    assert(expuestos.as[(java.sql.Date, String)].collect().map(_._2).toSeq == Seq("Staten Island"))

    val marcados = Privacidad.suprimirComplementariosTodos(
      Map("hora_zona" -> horaZona, "dia_barrio" -> db(("Staten Island", 11L), ("Manhattan", 900L))), k)
    val ocultos = marcados("dia_barrio").filter(col("complementario")).select("barrio_origen").as[String].collect()
    assert(ocultos.toSeq == Seq("Staten Island"))
    assert(marcados("hora_zona").filter(col("complementario")).isEmpty)
  }

  test("un día con suprimidos que no se delatan no oculta el total") {
    val horaZona = hz(("01", 23, "Staten Island", 4L), ("02", 23, "Staten Island", 7L))
    assert(Privacidad.padresExpuestos(horaZona, "hora_zona", k).isEmpty)
  }

  test("proteger suprime el complementario y no publica la marca") {
    val marcado = Privacidad.suprimirComplementarios(
      od(("Queens", "Bronx", 3), ("Queens", "Brooklyn", 12), ("Queens", "Manhattan", 15)), "od_dia_barrio", k)
      .withColumn("distancia_media", lit(1.0)).withColumn("importe_medio", lit(1.0))
      .withColumn("propina_media", lit(1.0)).withColumn("pct_pago_tarjeta", lit(1.0))
    val publicado = Privacidad.publicable(marcado, "od_dia_barrio", cfg.privacidad)
    assert(!publicado.columns.contains("complementario"))
    val suprimidos = publicado.filter(col("suprimido")).select("barrio_destino").as[String].collect().toSet
    assert(suprimidos == Set("Bronx", "Brooklyn"))
    assert(publicado.filter(col("suprimido") && col("n_viajes").isNotNull).isEmpty)
  }

  test("la curva de la muestra es coherente con lo que publica la carga histórica") {
    val publicado = mutable.Map.empty[String, DataFrame]
    val capturar: Publicacion.Publicador = (df, _, coleccion) => publicado(coleccion) = df.localCheckpoint()
    val tmp = Files.createTempDirectory("pids-curva").toUri.toString
    CargaHistorica.ejecutar(spark, cfg, muestra, "muestra", zonas, capturar, tmp)

    val validos = spark.read.parquet(s"$tmp/validos/historico/lote=muestra")
    val puntos = AnalisisPrivacidad.curva(Privacidad.conZonas(validos, zonas), Seq("dia_barrio", "hora_zona"),
      Seq(5, 10, 20))

    val hz10 = puntos.find(p => p.nivel == "hora_zona" && p.k == 10).get
    val publicadoHz = publicado("viajes_hora_zona")
    assert(hz10.grupos == publicadoHz.count())
    assert(hz10.suprimidosConComplementaria == publicadoHz.filter(col("suprimido")).count())
    assert(hz10.viajes == 991)

    // más k: más supresión y menos viajes publicados; la complementaria nunca suprime menos
    val hz = puntos.filter(_.nivel == "hora_zona").sortBy(_.k)
    assert(hz.map(_.suprimidos) == hz.map(_.suprimidos).sorted)
    assert(hz.map(_.viajesPublicados) == hz.map(_.viajesPublicados).sorted.reverse)
    assert(puntos.forall(p => p.suprimidosConComplementaria >= p.suprimidos))
    assert(puntos.forall(p => p.viajesPublicadosConComplementaria <= p.viajesPublicados))
  }

  test("el JSON de la curva solo lleva cifras agregadas") {
    val texto = AnalisisPrivacidad.json("entrada", Seq(AnalisisPrivacidad.Punto("hora_zona", 10, 100, 60, 65,
      1000, 950, 930)))
    assert(texto.contains("\"pct_viajes_publicados\" : 95.0"))
    assert(!texto.contains("recogida") && !texto.contains("lote"))
  }
}
