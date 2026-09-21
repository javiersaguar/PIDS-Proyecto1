/**
 * Gráfico de líneas (Recharts) con una o varias series sobre un eje temporal (horas o días). Las horas con
 * grupos enmascarados se marcan con un punto violeta en la base: no hay cifra que dibujar, pero sí hubo datos.
 */
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'

import { formatearEntero, pluralizar } from '@/componentes/datos/formato'
import { cn } from '@/lib/utils'

import { COLOR_BORDE, COLOR_ENMASCARADO, colorSerie, ESTILO_TICK } from './comun'
import { ContenedorGrafico } from './ContenedorGrafico'
import { TooltipGrafico, type DescribirEntrada } from './TooltipGrafico'

export interface Serie {
  /** Campo del punto con el valor de la serie. */
  clave: string
  nombre: string
  color?: string
}

export type PuntoLinea = Record<string, string | number | null | undefined>

interface Props {
  datos: readonly PuntoLinea[]
  /** Campo del punto con la etiqueta del eje X (una fecha ISO, normalmente). */
  claveX: string
  series: readonly Serie[]
  /** Campo con el número de grupos enmascarados en ese punto (se pintan como marcas violeta en la base). */
  claveEnmascarados?: string
  formatearX?: (valor: string) => string
  /** Formato completo de la etiqueta X en el tooltip (por defecto, el mismo que el eje). */
  formatearXCompleta?: (valor: string) => string
  formatearValor?: (valor: number) => string
  altura?: number
  /** Descripción accesible del gráfico. */
  titulo: string
  className?: string
}

const CLAVE_MARCA = '__marca_enmascarados'

export function GraficoLineas({
  datos,
  claveX,
  series,
  claveEnmascarados,
  formatearX = (v) => v,
  formatearXCompleta,
  formatearValor = formatearEntero,
  altura = 280,
  titulo,
  className,
}: Props) {
  const puntos = datos.map((p) => ({
    ...p,
    [CLAVE_MARCA]: claveEnmascarados && typeof p[claveEnmascarados] === 'number' && (p[claveEnmascarados] as number) > 0 ? 0 : null,
  }))
  const hayEnmascarados = puntos.some((p) => p[CLAVE_MARCA] === 0)
  const conPuntos = puntos.length <= 60

  const describirEntrada: DescribirEntrada = (clave, valor, punto) => {
    if (clave === CLAVE_MARCA) {
      const n = claveEnmascarados ? Number(punto[claveEnmascarados] ?? 0) : 0
      return n > 0 ? { texto: pluralizar(n, 'grupo enmascarado', 'grupos enmascarados'), enmascarado: true } : null
    }
    if (valor === null || valor === undefined) return { texto: '—' }
    return undefined
  }

  return (
    <figure className={cn('w-full', className)} aria-label={titulo} role="img">
      <ContenedorGrafico altura={altura}>
        {({ ancho }) => (
          <LineChart width={ancho} height={altura} data={puntos} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke={COLOR_BORDE} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey={claveX} tick={ESTILO_TICK} tickFormatter={(v: string) => formatearX(String(v))} axisLine={{ stroke: COLOR_BORDE }} tickLine={false} minTickGap={24} />
            <YAxis tick={ESTILO_TICK} tickFormatter={(v: number) => formatearValor(v)} axisLine={false} tickLine={false} allowDecimals={false} width={56} />
            {hayEnmascarados && <YAxis yAxisId="marcas" hide domain={[0, 1]} />}
            <Tooltip
              cursor={{ stroke: COLOR_BORDE }}
              content={<TooltipGrafico formatearValor={formatearValor} formatearEtiqueta={(e) => (formatearXCompleta ?? formatearX)(String(e))} describirEntrada={describirEntrada} />}
            />
            {series.length > 1 && <Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />}
            {series.map((serie, indice) => (
              <Line
                key={serie.clave}
                type="monotone"
                dataKey={serie.clave}
                name={serie.nombre}
                stroke={serie.color ?? colorSerie(indice)}
                strokeWidth={2}
                dot={conPuntos ? { r: 3, strokeWidth: 0, fill: serie.color ?? colorSerie(indice) } : false}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
            {hayEnmascarados && (
              <Line
                yAxisId="marcas"
                dataKey={CLAVE_MARCA}
                name="Grupos enmascarados"
                stroke="none"
                legendType="circle"
                dot={{ r: 4, fill: COLOR_ENMASCARADO, stroke: 'var(--superficie)', strokeWidth: 1.5 }}
                activeDot={{ r: 5, fill: COLOR_ENMASCARADO }}
                isAnimationActive={false}
              />
            )}
          </LineChart>
        )}
      </ContenedorGrafico>
    </figure>
  )
}
