package pids

import org.apache.spark.sql.functions._
import org.scalatest.funsuite.AnyFunSuite

class EsquemaSpec extends AnyFunSuite with SparkLocal {
  import spark.implicits._

  private def motivosDe(df: org.apache.spark.sql.DataFrame): Map[String, Long] =
    df.select(explode(col(Esquema.Motivos)).as("m")).groupBy("m").count()
      .collect().map(r => r.getString(0) -> r.getLong(1)).toMap

  test("la muestra da los mismos rechazos que la versión Python (tests/test_esquema.py)") {
    val bruto = spark.read.option("header", "true").csv(muestra)
    val validado = Esquema.validar(Esquema.normalizar(bruto, cfg.esquema), cfg.esquema)
    val motivos = motivosDe(validado)
    assert(validado.count() == 999)
    assert(motivos("fecha_fuera_de_rango") == 3)
    assert(motivos("importe_negativo") == 4)
    assert(motivos("duracion_no_positiva") == 1)
    assert(validado.filter(size(col(Esquema.Motivos)) > 0).count() == 8)
  }

  test("el formato de la API y el del CSV exportado dan el mismo viaje") {
    val csv = Seq(("1", "01/01/2020 12:28:15 AM", "01/01/2020 12:33:03 AM", "238", "239", "1.2", "6", "11.27"))
      .toDF("VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID",
        "trip_distance", "fare_amount", "total_amount")
    val api = Seq(("1", "2020-01-01T00:28:15.000", "2020-01-01T00:33:03.000", "238", "239", "1.20", "6", "11.27"))
      .toDF("vendorid", "tpep_pickup_datetime", "tpep_dropoff_datetime", "pulocationid", "dolocationid",
        "trip_distance", "fare_amount", "total_amount")
    val a = Esquema.normalizar(csv, cfg.esquema).collect().head
    val b = Esquema.normalizar(api, cfg.esquema).collect().head
    assert(a == b)
    assert(a.getAs[java.sql.Timestamp]("recogida").toString == "2020-01-01 00:28:15.0")
  }

  test("un Parquet con timestamps y columnas extra se normaliza y la columna que falta invalida") {
    val df = Seq((1L, java.sql.Timestamp.valueOf("2020-03-01 10:00:00"), java.sql.Timestamp.valueOf("2020-03-01 10:10:00"),
      1L, 2L, 1.0, 5.0, 7.0)).toDF("VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
      "PULocationID", "DOLocationID", "trip_distance", "fare_amount", "amount_total")
    val validado = Esquema.validar(Esquema.normalizar(df, cfg.esquema), cfg.esquema)
    assert(validado.select(Esquema.Motivos).as[Seq[String]].head() == Seq("falta_campo_obligatorio"))
  }

  test("la exportación completa (mes abreviado y decimales con coma) se normaliza igual") {
    val bruto = spark.read.option("header", "true").csv("../../data/muestra/exportacion_formato_europeo.csv")
    val validado = Esquema.validar(Esquema.normalizar(bruto, cfg.esquema), cfg.esquema)
    val (validos, rechazados) = Esquema.separar(validado, cfg.esquema)
    // de las 8 filas, una es de diciembre de 2019
    assert(validos.count() == 7)
    assert(rechazados.count() == 1)
    val fila = validos
      .filter(col("recogida") === lit(java.sql.Timestamp.valueOf("2020-01-01 00:28:15")))
      .collect().head
    assert(fila.getAs[Double]("distancia_millas") == 1.2)      // "1,2" en el fichero
    assert(fila.getAs[Double]("importe_total") == 11.27)       // "11,27"
    assert(fila.getAs[Int]("zona_origen") == 238)
  }

  test("tipar deja los códigos como enteros") {
    val bruto = spark.read.option("header", "true").csv(muestra)
    val (validos, _) = Esquema.separar(Esquema.validar(Esquema.normalizar(bruto, cfg.esquema), cfg.esquema), cfg.esquema)
    assert(validos.schema("vendor_id").dataType.typeName == "integer")
    assert(validos.count() == 991)
  }
}
