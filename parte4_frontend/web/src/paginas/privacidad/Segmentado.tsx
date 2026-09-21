/**
 * Control segmentado accesible (`radiogroup`) para filtros con pocas opciones: horas de la auditoría,
 * resultado de las decisiones…
 */
import { cn } from '@/lib/utils'

export interface OpcionSegmentada<T extends string | number> {
  valor: T
  etiqueta: string
}

interface Props<T extends string | number> {
  etiqueta: string
  opciones: readonly OpcionSegmentada<T>[]
  valor: T
  alCambiar: (valor: T) => void
  className?: string
}

export function Segmentado<T extends string | number>({ etiqueta, opciones, valor, alCambiar, className }: Props<T>) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className={cn('inline-flex items-center rounded-lg bg-slate-100 p-0.5', className)}>
      {opciones.map((opcion) => {
        const activo = opcion.valor === valor
        return (
          <button
            key={String(opcion.valor)}
            type="button"
            role="radio"
            aria-checked={activo}
            onClick={() => alCambiar(opcion.valor)}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring',
              activo ? 'bg-primario text-white shadow-sm' : 'text-texto-suave hover:bg-muted hover:text-foreground',
            )}
          >
            {opcion.etiqueta}
          </button>
        )
      })}
    </div>
  )
}
