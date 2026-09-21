/**
 * Gráfico de barras (Recharts) con una serie: horizontal (categorías en el eje Y, para barrios o zonas) o
 * vertical (para horas). La serie va en el amarillo taxi; los grupos enmascarados se pintan como una barra
 * mínima con trama violeta y la etiqueta «<10», sin cifra.
 */
import { Bar, BarChart, CartesianGrid, Cell, LabelList, Tooltip, XAxis, YAxis } from 'recharts'

import { formatearEntero } from '@/componentes/datos/formato'
import { cn } from '@/lib/utils'

import { anchoEjeCategorias, COLOR_BORDE, COLOR_CURSOR, COLOR_ENMASCARADO, COLOR_PRINCIPAL, ESTILO_TICK, ID_TRAMA_ENMASCARADO } from './comun'
import { ContenedorGrafico } from './ContenedorGrafico'
import { TooltipGrafico, type DescribirEntrada } from './TooltipGrafico'

export interface Barra {
  /** Etiqueta de la categoría (barrio, zona, hora…). */
  etiqueta: string
  /** Valor de la barra; `null` si no hay cifra (grupo enmascarado). */
  valor: number | null
  enmascarado?: boolean
  /** Texto adicional para el tooltip (por ejemplo, «3 grupos, 1 enmascarado»). */
  detalle?: string
}

interface Props {
  datos: readonly Barra[]
  /** `horizontal`: barras de izquierda a derecha (categorías en Y). `vertical`: columnas. */
  orientacion?: 'horizontal' | 'vertical'
  /** Alto en píxeles; en horizontal se calcula según el número de barras si no se indica. */
  altura?: number
  nombreSerie?: string
  color?: string
  formatearValor?: (valor: number) => string
  /** Formato de las etiquetas de categoría en el eje (el tooltip usa `formatearEtiquetaCompleta`). */
  formatearEtiqueta?: (etiqueta: string) => string
  formatearEtiquetaCompleta?: (etiqueta: string) => string
  /** Cifras al final de cada barra. */
  conEtiquetas?: boolean
  /** Descripción accesible del gráfico. */
  titulo: string
  className?: string
}

interface PuntoBarra extends Barra {
  /** Lo que se dibuja: 0 en los enmascarados (la barra mínima la pone `minPointSize`). */
  dibujado: number
}

export function GraficoBarras({
  datos,
  orientacion = 'horizontal',
  altura,
  nombreSerie = 'Viajes',
  color = COLOR_PRINCIPAL,
  formatearValor = formatearEntero,
  formatearEtiqueta = (e) => e,
  formatearEtiquetaCompleta,
  conEtiquetas = true,
  titulo,
  className,
}: Props) {
  const horizontal = orientacion === 'horizontal'
  const puntos: PuntoBarra[] = datos.map((d) => ({ ...d, dibujado: d.enmascarado || d.valor === null ? 0 : d.valor }))
  const alto = altura ?? (horizontal ? Math.max(140, puntos.length * 30 + 36) : 260)
  const etiquetas = puntos.map((p) => formatearEtiqueta(p.etiqueta))
  const hayEnmascarados = puntos.some((p) => p.enmascarado)

  const describirEntrada: DescribirEntrada = (_clave, _valor, punto) => {
    const p = punto as unknown as PuntoBarra
    if (p.enmascarado) return { texto: '<10 · enmascarado', enmascarado: true }
    return p.valor === null ? { texto: '—' } : { texto: formatearValor(p.valor) }
  }

  return (
    <figure className={cn('w-full', className)} aria-label={titulo} role="img">
      <ContenedorGrafico altura={alto}>
        {({ ancho }) => (
          <BarChart
            width={ancho}
            height={alto}
            data={puntos}
            layout={horizontal ? 'vertical' : 'horizontal'}
            margin={{ top: 8, right: conEtiquetas && horizontal ? 56 : 16, bottom: 4, left: 4 }}
            barCategoryGap={horizontal ? 6 : '20%'}
          >
            <defs>
              <pattern id={ID_TRAMA_ENMASCARADO} patternUnits="userSpaceOnUse" width={6} height={6} patternTransform="rotate(45)">
                <rect width={6} height={6} fill="var(--enmascarado-suave)" />
                <line x1={0} y1={0} x2={0} y2={6} stroke={COLOR_ENMASCARADO} strokeWidth={2} />
              </pattern>
            </defs>
            <CartesianGrid stroke={COLOR_BORDE} strokeDasharray="3 3" horizontal={!horizontal} vertical={horizontal} />
            {horizontal ? (
              <>
                <XAxis type="number" tick={ESTILO_TICK} tickFormatter={(v: number) => formatearValor(v)} axisLine={false} tickLine={false} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="etiqueta"
                  tick={ESTILO_TICK}
                  tickFormatter={formatearEtiqueta}
                  width={anchoEjeCategorias(etiquetas)}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                />
              </>
            ) : (
              <>
                <XAxis type="category" dataKey="etiqueta" tick={ESTILO_TICK} tickFormatter={formatearEtiqueta} axisLine={{ stroke: COLOR_BORDE }} tickLine={false} interval="preserveStartEnd" />
                <YAxis type="number" tick={ESTILO_TICK} tickFormatter={(v: number) => formatearValor(v)} axisLine={false} tickLine={false} allowDecimals={false} width={56} />
              </>
            )}
            <Tooltip
              cursor={{ fill: COLOR_CURSOR }}
              content={
                <TooltipGrafico
                  formatearValor={formatearValor}
                  formatearEtiqueta={(e) => (formatearEtiquetaCompleta ?? formatearEtiqueta)(String(e))}
                  describirEntrada={describirEntrada}
                  detalle={(p) => (p as unknown as PuntoBarra).detalle}
                />
              }
            />
            <Bar
              dataKey="dibujado"
              name={nombreSerie}
              fill={color}
              radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]}
              minPointSize={(_valor, indice) => (puntos[indice]?.enmascarado ? 8 : 0)}
              isAnimationActive={false}
              maxBarSize={horizontal ? 26 : 48}
            >
              {puntos.map((p) => (
                <Cell key={p.etiqueta} fill={p.enmascarado ? `url(#${ID_TRAMA_ENMASCARADO})` : color} stroke={p.enmascarado ? COLOR_ENMASCARADO : undefined} />
              ))}
              {conEtiquetas && (
                <LabelList
                  position={horizontal ? 'right' : 'top'}
                  offset={6}
                  fill="var(--texto)"
                  fontSize={11}
                  className="cifra"
                  valueAccessor={(entrada) => {
                    const p = entrada.payload as PuntoBarra
                    return p.enmascarado || p.valor === null ? '' : formatearValor(p.valor)
                  }}
                />
              )}
              {conEtiquetas && hayEnmascarados && (
                <LabelList
                  position={horizontal ? 'right' : 'top'}
                  offset={6}
                  fill={COLOR_ENMASCARADO}
                  fontSize={11}
                  fontWeight={600}
                  valueAccessor={(entrada) => ((entrada.payload as PuntoBarra).enmascarado ? '<10' : '')}
                />
              )}
            </Bar>
          </BarChart>
        )}
      </ContenedorGrafico>
    </figure>
  )
}
