package pids

import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types.{DoubleType, LongType}
import org.apache.spark.sql.{Column, DataFrame}

/** Reglas propias de privacidad al publicar (E3).
  *
  *  - Solo salen agregados, nunca viajes: por hora y zona de origen, por día y barrio, y flujos
  *    entre barrios por día. El destino no se publica a nivel de hora ni de zona.
  *  - Los grupos con menos de `k_minimo` viajes se publican marcados como `suprimido`, sin cifras.
  *  - Supresión complementaria (solo en lotes): si restando al total del día y barrio los grupos
  *    visibles se pudiera despejar un grupo suprimido, se suprime también otro; y si no hay ninguno
  *    visible que suprimir, se oculta el total (ver `suprimirComplementariosTodos`).
  *  - Las medias se redondean.
  *
  * Salvo la supresión complementaria, las mismas funciones sirven para lotes y para streaming (las
  * ventanas de `window` funcionan en los dos modos).
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

  /** Partición «padre» de cada nivel: sus grupos suman un total que también se publica (viajes por día
    * y barrio). Es lo que permite el ataque por diferencia; los niveles sin padre no lo sufren. */
  private val particionPadre: Map[String, (Seq[String], Seq[String])] = Map(
    // nivel -> (columnas de la partición, columnas para desempatar de forma determinista)
    "hora_zona"     -> (Seq("_dia", "barrio_origen"), Seq("hora", "zona_origen")),
    "od_dia_barrio" -> (Seq("dia", "barrio_origen"), Seq("barrio_destino"))
  )

  /** ¿Quedan fijados (o casi) los grupos suprimidos de una partición, sabiendo cuántos son (`c`) y cuánto
    * suman (`oculto`)? El atacante supone que cada uno tiene entre 1 y k-1 viajes: si el rango posible
    * de cada grupo es de uno o dos valores, la partición está expuesta. Es la misma cuenta que hace
    * scripts/ataque_diferencia.py. */
  private def expuesta(c: Column, oculto: Column, k: Int): Column = {
    val minimo = greatest(lit(1L), oculto - (c - 1) * (k - 1))
    val maximo = least(lit((k - 1).toLong), oculto - (c - 1))
    c >= 1 && (maximo - minimo) <= 1
  }

  /** Supresión complementaria contra el ataque por diferencia (docs/escenario_E3.md).
    *
    * En cada partición (día, barrio), el atacante conoce el total del día y los grupos visibles, así
    * que sabe cuánto suman los suprimidos. Si con eso el valor de cada suprimido queda fijado o casi
    * (rango de uno o dos valores, suponiendo que todos tienen entre 1 y k-1 viajes; por ejemplo, un
    * único suprimido, o diez que suman diez), se suprime también el grupo visible más pequeño. Como
    * ese grupo tiene k o más viajes, la suma oculta deja de ser despejable.
    *
    * Añade la columna `complementario`, que respeta `proteger` y que NUNCA se publica: si el atacante
    * supiera cuál es el grupo complementario, volvería a despejar el otro.
    *
    * Necesita la partición completa (el día entero), así que solo sirve para lotes; en streaming los
    * días están a medias en cada micro-lote.
    */
  def suprimirComplementarios(agregado: DataFrame, nivel: String, k: Int): DataFrame =
    particionPadre.get(nivel) match {
      case None => agregado.withColumn("complementario", lit(false))
      case Some((claves, desempate)) =>
        val base = if (claves.contains("_dia")) agregado.withColumn("_dia", to_date(col("hora"))) else agregado
        val particion = Window.partitionBy(claves.map(col): _*)
        val pequeno = col("n_viajes") < k
        // el más pequeño de los visibles es el primero con pequeno = false al ordenar por n_viajes
        val orden = particion.orderBy((pequeno.asc +: col("n_viajes").asc +: desempate.map(c => col(c).asc)): _*)
        base
          .withColumn("_c", sum(when(pequeno, 1L).otherwise(0L)).over(particion))
          .withColumn("_oculto", sum(when(pequeno, col("n_viajes")).otherwise(0L)).over(particion))
          .withColumn("_expuesta", expuesta(col("_c"), col("_oculto"), k))
          .withColumn("_orden", row_number().over(orden))
          .withColumn("complementario", col("_expuesta") && !pequeno && col("_orden") === 1)
          .drop("_c", "_oculto", "_expuesta", "_orden", "_dia")
    }

  /** Particiones (día, barrio) expuestas que NO tienen ningún grupo visible: la supresión complementaria
    * no puede arreglarlas (no hay nada más que suprimir en ese nivel), así que hay que ocultar su total,
    * que es el grupo del nivel dia_barrio. Caso típico: un día de Staten Island con once grupos
    * hora-zona de un viaje cada uno y un total de 11. Devuelve las claves (dia, barrio_origen). */
  def padresExpuestos(agregado: DataFrame, nivel: String, k: Int): DataFrame =
    particionPadre.get(nivel) match {
      case None => throw new IllegalArgumentException(s"el nivel $nivel no tiene partición padre")
      case Some((claves, _)) =>
        val base = if (claves.contains("_dia")) agregado.withColumn("_dia", to_date(col("hora"))) else agregado
        val pequeno = col("n_viajes") < k
        base.groupBy(claves.map(col): _*)
          .agg(sum(when(pequeno, 1L).otherwise(0L)).as("_c"),
            sum(when(pequeno, col("n_viajes")).otherwise(0L)).as("_oculto"),
            sum(when(pequeno, 0L).otherwise(1L)).as("_visibles"))
          .filter(expuesta(col("_c"), col("_oculto"), k) && col("_visibles") === 0)
          .select(col(claves.head).as("dia"), col("barrio_origen"))
    }

  /** Marca como complementarios los totales día-barrio de las particiones expuestas sin visibles. */
  def suprimirPadres(diaBarrio: DataFrame, expuestos: DataFrame): DataFrame = {
    val base = if (diaBarrio.columns.contains("complementario")) diaBarrio
               else diaBarrio.withColumn("complementario", lit(false))
    val marcas = expuestos.distinct().withColumn("_padre_expuesto", lit(true))
    base.join(broadcast(marcas), Seq("dia", "barrio_origen"), "left")
      .withColumn("complementario", col("complementario") || coalesce(col("_padre_expuesto"), lit(false)))
      .drop("_padre_expuesto")
  }

  /** Aplica las dos supresiones complementarias a los agregados de todos los niveles de una carga:
    * dentro de cada nivel y, para las particiones sin arreglo, en su total día-barrio. */
  def suprimirComplementariosTodos(agregados: Map[String, DataFrame], k: Int): Map[String, DataFrame] = {
    val expuestos = agregados.toSeq.collect {
      case (nivel, agregado) if particionPadre.contains(nivel) => padresExpuestos(agregado, nivel, k)
    }.reduceOption(_ union _)
    agregados.map { case (nivel, agregado) =>
      val marcado = suprimirComplementarios(agregado, nivel, k)
      nivel -> (if (nivel == "dia_barrio") expuestos.fold(marcado)(suprimirPadres(marcado, _)) else marcado)
    }
  }

  /** Suprime los grupos pequeños (y los complementarios, si vienen marcados) y redondea. */
  def proteger(agregado: DataFrame, cfg: ConfigPrivacidad): DataFrame = {
    val complementario = if (agregado.columns.contains("complementario")) col("complementario") else lit(false)
    val conMarca = agregado
      .withColumn("suprimido", col("n_viajes") < cfg.kMinimo || complementario)
      .drop("complementario")
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
