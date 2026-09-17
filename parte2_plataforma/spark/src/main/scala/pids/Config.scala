package pids

import com.fasterxml.jackson.databind.{JsonNode, ObjectMapper}

import java.nio.file.{Files, Path, Paths}
import scala.jdk.CollectionConverters._

/** Reglas compartidas con Python: config/esquema_viaje.json y config/privacidad.json. */
final case class ConfigEsquema(
    alias: Seq[(String, String)],          // nombre en la fuente (minúsculas) -> nombre canónico
    enteras: Set[String],
    fechas: Set[String],
    texto: Set[String],
    formatosFecha: Seq[String],
    decimalComa: Boolean,
    obligatorias: Seq[String],
    recogidaDesde: String,
    recogidaHasta: String,
    duracionMaximaHoras: Int,
    distanciaMaxima: Double,
    zonaMinima: Int,
    zonaMaxima: Int,
    vendors: Seq[Int],
    tarifas: Seq[Int],
    tiposPago: Seq[Int],
    indicadores: Seq[String]
) {
  def columnas: Seq[String] = alias.map(_._2)
}

final case class Nivel(nombre: String, coleccion: String, dimensiones: Seq[String])

final case class ConfigPrivacidad(
    version: Int,
    kMinimo: Int,
    decimales: Int,
    metricas: Seq[String],
    niveles: Map[String, Nivel],
    prefijos: Map[String, String]   // fuente -> prefijo de colección ("" o "tr_")
) {
  def coleccion(nivel: String, fuente: String): String = prefijos(fuente) + niveles(nivel).coleccion
}

final case class Config(esquema: ConfigEsquema, privacidad: ConfigPrivacidad)

object Config {
  private val mapper = new ObjectMapper()

  def directorio: Path = Paths.get(sys.env.getOrElse("PIDS_CONFIG_DIR", "/opt/pids/config"))

  def cargar(dir: Path = directorio): Config =
    Config(esquema(leer(dir.resolve("esquema_viaje.json"))), privacidad(leer(dir.resolve("privacidad.json"))))

  private def leer(ruta: Path): JsonNode = mapper.readTree(Files.readString(ruta))

  private def textos(n: JsonNode): Seq[String] = n.elements().asScala.map(_.asText()).toSeq
  private def enteros(n: JsonNode): Seq[Int] = n.elements().asScala.map(_.asInt()).toSeq

  private def esquema(j: JsonNode): ConfigEsquema = {
    val r = j.get("reglas")
    ConfigEsquema(
      alias = j.get("alias").fields().asScala.map(e => e.getKey -> e.getValue.asText()).toSeq,
      enteras = textos(j.get("enteras")).toSet,
      fechas = textos(j.get("fechas")).toSet,
      texto = textos(j.get("texto")).toSet,
      formatosFecha = textos(j.get("formatos_fecha")),
      decimalComa = j.get("decimal_coma").asBoolean(false),
      obligatorias = textos(j.get("obligatorias")),
      recogidaDesde = r.get("recogida_desde").asText(),
      recogidaHasta = r.get("recogida_hasta").asText(),
      duracionMaximaHoras = r.get("duracion_maxima_horas").asInt(),
      distanciaMaxima = r.get("distancia_maxima_millas").asDouble(),
      zonaMinima = r.get("zona_minima").asInt(),
      zonaMaxima = r.get("zona_maxima").asInt(),
      vendors = enteros(r.get("vendor_id")),
      tarifas = enteros(r.get("tarifa_id")),
      tiposPago = enteros(r.get("tipo_pago")),
      indicadores = textos(r.get("almacenado_y_reenviado"))
    )
  }

  private def privacidad(j: JsonNode): ConfigPrivacidad = ConfigPrivacidad(
    version = j.get("version").asInt(),
    kMinimo = j.get("k_minimo").asInt(),
    decimales = j.get("decimales").asInt(),
    metricas = textos(j.get("metricas")),
    niveles = j.get("niveles").fields().asScala.map { e =>
      e.getKey -> Nivel(e.getKey, e.getValue.get("coleccion").asText(), textos(e.getValue.get("dimensiones")))
    }.toMap,
    prefijos = j.get("fuentes").fields().asScala.map(e => e.getKey -> e.getValue.asText()).toMap
  )
}
