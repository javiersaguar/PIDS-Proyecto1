/**
 * El gráfico del resultado según el nivel: líneas por hora, barras por barrio (o líneas por día si hay varios) y
 * matriz origen → destino para los flujos. Con un selector de métrica si la consulta pidió más de una.
 */
import { useMemo, useState } from 'react'

import type { Metrica, Respuesta } from '@/api/tipos'
import { ETIQUETAS_METRICA, formatearMetrica } from '@/componentes/datos/agregados'
import { formatearFecha, formatearFechaCorta, formatearFechaHora, formatearHora, pluralizar } from '@/componentes/datos/formato'
import { GraficoBarras, GraficoLineas, MatrizFlujos } from '@/componentes/graficos'
import { EstadoVacio } from '@/componentes/shell'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'

import { normalizarMetricas } from './consulta'
import { barrasPorBarrio, celdasFlujos, CLAVE_ENMASCARADOS, diasDistintos, lineasPorDia, lineasPorHora, MAX_SERIES } from './series'

interface Props {
  respuesta: Respuesta
}

export function GraficoResultado({ respuesta }: Props) {
  const metricas = useMemo(() => normalizarMetricas(respuesta.consulta.metricas), [respuesta.consulta.metricas])
  const [metrica, setMetrica] = useState<Metrica>('n_viajes')
  const metricaActiva: Metrica = metricas.includes(metrica) ? metrica : 'n_viajes'
  const formatearValor = (v: number) => formatearMetrica(metricaActiva, v)
  const { filas, consulta } = respuesta

  if (filas.length === 0) {
    return <EstadoVacio titulo="Nada que dibujar" descripcion="La consulta no ha devuelto ningún grupo en esa ventana." />
  }

  return (
    <div className="space-y-3">
      {metricas.length > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Label htmlFor="metrica-grafico" className="text-xs text-texto-suave">
            Métrica del gráfico
          </Label>
          <Select value={metricaActiva} onValueChange={(v) => setMetrica(v as Metrica)}>
            <SelectTrigger id="metrica-grafico" size="sm" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {metricas.map((m) => (
                <SelectItem key={m} value={m}>
                  {ETIQUETAS_METRICA[m]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {consulta.nivel === 'hora_zona' && <GraficoHoras respuesta={respuesta} metrica={metricaActiva} formatearValor={formatearValor} />}
      {consulta.nivel === 'dia_barrio' && <GraficoBarrios respuesta={respuesta} metrica={metricaActiva} formatearValor={formatearValor} />}
      {consulta.nivel === 'od_dia_barrio' && <GraficoFlujos respuesta={respuesta} metrica={metricaActiva} formatearValor={formatearValor} />}
    </div>
  )
}

interface PropsGrafico {
  respuesta: Respuesta
  metrica: Metrica
  formatearValor: (v: number) => string
}

function GraficoHoras({ respuesta, metrica, formatearValor }: PropsGrafico) {
  const datos = useMemo(() => lineasPorHora(respuesta.filas, metrica), [respuesta.filas, metrica])
  const variosDias = useMemo(() => new Set(datos.puntos.map((p) => String(p.hora).slice(0, 10))).size > 1, [datos.puntos])
  return (
    <>
      <GraficoLineas
        datos={datos.puntos}
        claveX="hora"
        series={datos.series}
        claveEnmascarados={CLAVE_ENMASCARADOS}
        formatearX={(v) => (variosDias ? `${formatearFechaCorta(v)} ${formatearHora(v)}` : formatearHora(v))}
        formatearXCompleta={formatearFechaHora}
        formatearValor={formatearValor}
        titulo={`${ETIQUETAS_METRICA[metrica]} por hora`}
      />
      <p className="text-xs text-texto-suave">
        {datos.modo === 'series'
          ? `Una línea por zona de origen (${pluralizar(datos.categorias, 'zona')}).`
          : `${pluralizar(datos.categorias, 'zona')} de origen: se muestra ${metrica === 'n_viajes' ? 'la suma' : 'la media ponderada por viajes'} de los grupos visibles de cada hora (más de ${MAX_SERIES} zonas no caben como líneas).`}{' '}
        Los puntos violeta marcan horas con grupos enmascarados, que no se suman.
      </p>
    </>
  )
}

function GraficoBarrios({ respuesta, metrica, formatearValor }: PropsGrafico) {
  const dias = useMemo(() => diasDistintos(respuesta.filas), [respuesta.filas])
  const barras = useMemo(() => (dias.length <= 1 ? barrasPorBarrio(respuesta.filas, metrica) : []), [respuesta.filas, metrica, dias.length])
  const lineas = useMemo(() => (dias.length > 1 ? lineasPorDia(respuesta.filas, metrica) : null), [respuesta.filas, metrica, dias.length])

  if (lineas) {
    return (
      <>
        <GraficoLineas
          datos={lineas.puntos}
          claveX="dia"
          series={lineas.series}
          claveEnmascarados={CLAVE_ENMASCARADOS}
          formatearX={formatearFechaCorta}
          formatearXCompleta={formatearFecha}
          formatearValor={formatearValor}
          titulo={`${ETIQUETAS_METRICA[metrica]} por día`}
        />
        <p className="text-xs text-texto-suave">
          {pluralizar(dias.length, 'día')};{' '}
          {lineas.modo === 'series' ? `una línea por barrio de origen (${pluralizar(lineas.categorias, 'barrio')}).` : `se muestra el agregado de los grupos visibles de cada día.`} Los puntos
          violeta marcan días con grupos enmascarados, que no se suman.
        </p>
      </>
    )
  }

  return (
    <>
      <GraficoBarras datos={barras} orientacion="horizontal" nombreSerie={ETIQUETAS_METRICA[metrica]} formatearValor={formatearValor} titulo={`${ETIQUETAS_METRICA[metrica]} por barrio de origen`} />
      <p className="text-xs text-texto-suave">
        {dias[0] ? `${formatearFecha(dias[0])} · ` : ''}
        Barras por barrio de origen; los barrios enmascarados (menos de 10 viajes) aparecen con trama violeta y «&lt;10».
      </p>
    </>
  )
}

function GraficoFlujos({ respuesta, metrica, formatearValor }: PropsGrafico) {
  const celdas = useMemo(() => celdasFlujos(respuesta.filas, metrica), [respuesta.filas, metrica])
  const dias = useMemo(() => diasDistintos(respuesta.filas), [respuesta.filas])
  return (
    <>
      <MatrizFlujos celdas={celdas} formatearValor={formatearValor} titulo={`${ETIQUETAS_METRICA[metrica]} de origen a destino`} />
      <p className="text-xs text-texto-suave">
        {dias.length > 1
          ? `${pluralizar(dias.length, 'día')} agregados: cada celda ${metrica === 'n_viajes' ? 'suma' : 'promedia (ponderando por viajes)'} los grupos visibles del par origen → destino.`
          : `Flujos del ${formatearFecha(dias[0])}.`}
      </p>
    </>
  )
}
