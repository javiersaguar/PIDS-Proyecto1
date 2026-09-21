/**
 * Barras pequeñas de un KPI: cada valor es una barra, con escala de raíz para que los barrios
 * pequeños no desaparezcan junto al mayor.
 */
import { cn } from '@/lib/utils'

interface Props {
  valores: readonly number[]
  /** Un color para todas, o uno por barra. */
  color?: string
  colores?: readonly string[]
  className?: string
}

export function MiniBarras({ valores, color = '#3b82f6', colores, className }: Props) {
  const limpios = valores.filter((valor) => Number.isFinite(valor) && valor >= 0)
  if (limpios.length === 0) return null
  const ancho = 92
  const alto = 46
  const hueco = limpios.length > 5 ? 3 : 5
  const grosor = (ancho - hueco * (limpios.length - 1)) / limpios.length
  const maximo = Math.max(...limpios, 1)

  return (
    <svg viewBox={`0 0 ${ancho} ${alto}`} className={cn('h-12 w-[5.75rem] shrink-0', className)} aria-hidden>
      {limpios.map((valor, indice) => {
        const fraccion = Math.sqrt(valor / maximo)
        const altura = Math.max(valor > 0 ? 5 : 2, fraccion * (alto - 2))
        const x = indice * (grosor + hueco)
        return (
          <rect
            key={indice}
            x={x}
            y={alto - altura}
            width={grosor}
            height={altura}
            rx={Math.min(4, grosor / 2)}
            fill={colores?.[indice] ?? color}
            opacity={0.45 + fraccion * 0.55}
          />
        )
      })}
    </svg>
  )
}
