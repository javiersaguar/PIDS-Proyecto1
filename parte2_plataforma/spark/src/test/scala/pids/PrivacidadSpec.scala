package pids

import org.apache.spark.sql.DataFrame
import org.apache.spark.sql.functions._
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.Files
import scala.collection.mutable

class PrivacidadSpec extends AnyFunSuite with SparkLocal {
  import spark.implicits._

  /** Campos que nunca pueden aparecer en lo publicado. */
  private val individuales = Set("recogida", "llegada", "lote", "vendor_id", "pasajeros", "tarifa", "propina",
    "importe_total", "zona_destino", "distancia_millas", "tipo_pago", "motivos")

  test("los grupos con menos de k viajes se publican sin cifras") {
    val k = cfg.privacidad.kMinimo
    val agregado = Seq((1, k - 1L, 3.456), (2, k.toLong, 4.321)).toDF("zona", "n_viajes", "importe_medio")
      .withColumn("distancia_media", lit(1.0)).withColumn("propina_media", lit(1.0))
      .withColumn("pct_pago_tarjeta", lit(50.0))
    val filas = Privacidad.proteger(agregado, cfg.privacidad).orderBy("zona").collect()
    assert(filas(0).getAs[Boolean]("suprimido"))
    assert(filas(0).isNullAt(filas(0).fieldIndex("n_viajes")))
    assert(filas(0).isNullAt(filas(0).fieldIndex("importe_medio")))
    assert(!filas(1).getAs[Boolean]("suprimido"))
    assert(filas(1).getAs[Double]("importe_medio") == 4.32)
  }

  test("la carga histórica de la muestra solo publica agregados, con _id y nivel") {
    val publicado = mutable.Map.empty[String, DataFrame]
    val capturar: Publicacion.Publicador = (df, base, coleccion) => {
      assert(base == "publico")
      publicado(coleccion) = df.localCheckpoint()
    }
    val tmp = Files.createTempDirectory("pids-crudo").toUri.toString
    val resumen = CargaHistorica.ejecutar(spark, cfg, muestra, "muestra", zonas, capturar, tmp)

    assert(resumen.validos == 991 && resumen.rechazados == 8)
    assert(publicado.keySet == Set("viajes_hora_zona", "viajes_dia_barrio", "od_dia_barrio"))
    publicado.foreach { case (coleccion, df) =>
      val filtrados = df.columns.toSet & individuales
      assert(filtrados.isEmpty, s"$coleccion publica campos individuales: $filtrados")
      assert(df.filter(col("_id").isNull).isEmpty)
      assert(df.filter(!col("suprimido") && col("n_viajes") < cfg.privacidad.kMinimo).isEmpty)
    }
    // 999 viajes en ~80 zonas y 5 horas: la mayoría de grupos hora-zona deben quedar suprimidos
    assert(resumen.grupos_suprimidos("hora_zona") > resumen.grupos_publicados("hora_zona") / 2)
    // y la zona restringida recibe los viajes válidos
    assert(spark.read.parquet(s"$tmp/validos/historico/lote=muestra").count() == 991)
  }

  test("el evento de tiempo real se desenvuelve igual que una fila de CSV") {
    val json = """{"registro": {"VendorID": 1, "tpep_pickup_datetime": "2020-01-01T00:28:15",""" +
      """ "tpep_dropoff_datetime": "2020-01-01T00:33:03", "PULocationID": 238, "DOLocationID": 239,""" +
      """ "trip_distance": 1.2, "fare_amount": 6, "total_amount": 11.27}, "origen": "tiempo_real", "lote": "l1"}"""
    val eventos = Seq(json.getBytes("UTF-8")).toDF("value")
    val fila = Esquema.validar(
      Esquema.normalizar(TiempoReal.desenvolver(eventos, cfg.esquema), cfg.esquema, Seq("lote")), cfg.esquema)
      .collect().head
    assert(fila.getAs[Seq[String]](Esquema.Motivos).isEmpty)
    assert(fila.getAs[Double]("zona_origen") == 238.0)
    assert(fila.getAs[String]("lote") == "l1")
  }
}
