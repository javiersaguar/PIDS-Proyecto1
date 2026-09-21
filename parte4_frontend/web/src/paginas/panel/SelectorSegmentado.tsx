/**
 * Control segmentado del panel (el de «Mensual / Trimestral / Anual» del cuadro de mando): un botón activo
 * en blanco sobre una pista gris clara.
 */
import { cn } from '@/lib/utils'

interface Opcion<T extends string> {
  valor: T
  texto: string
}

interface Props<T extends string> {
  etiqueta: string
  valor: T
  opciones: readonly Opcion<T>[]
  alCambiar: (valor: T) => void
}

export function SelectorSegmentado<T extends string>({ etiqueta, valor, opciones, alCambiar }: Props<T>) {
  return (
    <div role="tablist" aria-label={etiqueta} className="inline-flex rounded-lg bg-slate-100 p-0.5">
      {opciones.map((opcion) => {
        const activo = opcion.valor === valor
        return (
          <button
            key={opcion.valor}
            type="button"
            role="tab"
            aria-selected={activo}
            onClick={() => alCambiar(opcion.valor)}
            className={cn(
              'rounded-md px-3 py-1 text-xs font-medium transition-colors',
              activo ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700',
            )}
          >
            {opcion.texto}
          </button>
        )
      })}
    </div>
  )
}
