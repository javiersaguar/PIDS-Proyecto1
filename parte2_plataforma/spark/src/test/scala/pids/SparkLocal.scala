package pids

import org.apache.spark.sql.SparkSession
import org.scalatest.{BeforeAndAfterAll, Suite}

import java.nio.file.Paths

trait SparkLocal extends BeforeAndAfterAll { self: Suite =>
  lazy val spark: SparkSession = SparkSession.builder()
    .master("local[2]")
    .appName("pids-tests")
    .config("spark.sql.session.timeZone", "UTC")
    .config("spark.sql.shuffle.partitions", "2")
    .config("spark.ui.enabled", "false")
    .getOrCreate()

  lazy val cfg: Config = Config.cargar(Paths.get(sys.env.getOrElse("PIDS_CONFIG_DIR", "../../config")))

  val muestra = "../../data/muestra/yellow_tripdata_2020_muestra.csv"

  /** Tabla de zonas mínima para no depender de descargas en los tests. */
  def zonas = {
    import spark.implicits._
    (1 to 265).map(i => (i.toString, if (i % 2 == 0) "Manhattan" else "Queens", s"Zona $i", "Yellow Zone"))
      .toDF("LocationID", "Borough", "Zone", "service_zone")
  }

  override def afterAll(): Unit = {
    spark.stop()
    super.afterAll()
  }
}
