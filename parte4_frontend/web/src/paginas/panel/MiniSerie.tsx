/**
 * Chispa decorativa de las tarjetas KPI: una línea con el relleno desvanecido, como en un cuadro de mando.
 * No es una serie temporal; solo resume la forma de los valores que ya muestra la tarjeta. Cuando los valores
 * cambian, la línea se desliza hacia la forma nueva.
 */
import { useId } from 'react'

import { useValoresAnimados } from '@/componentes/datos/useNumeroAnimado'
import { cn } from '@/lib/utils'

interface Props {
  valores: readonly number[]
  color: string
  className?: string
}

export function MiniSerie({ valores, color, className }: Props) {
  const id = `mini-${useId().replace(/:/g, '')}`
  const limpios = useValoresAnimados(valores.filter((valor) => Number.isFinite(valor)))
  if (limpios.length < 2) return null

  const ancho = 96
  const alto = 36
  const minimo = Math.min(...limpios)
  const maximo = Math.max(...limpios)
  const rango = maximo - minimo || 1
  const puntos = limpios.map((valor, indice) => {
    const x = (indice / (limpios.length - 1)) * ancho
    const y = alto - 2 - ((valor - minimo) / rango) * (alto - 6)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const linea = `M${puntos.join(' L')}`
  const area = `${linea} L${ancho},${alto} L0,${alto} Z`

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className={cn('h-12 w-24 shrink-0', className)} aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.38" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <path d={linea} fill="none" stroke={color} strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
