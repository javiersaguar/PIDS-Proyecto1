/**
 * Desplegable ligero (botón con `aria-expanded` + panel) para los pasos y las fuentes de cada respuesta.
 * Se controla desde fuera con `abierto`/`alCambiar` o solo por dentro si no se pasan.
 */
import { ChevronRight } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface Props {
  titulo: ReactNode
  children: ReactNode
  abierto?: boolean
  alCambiar?: (abierto: boolean) => void
  /** Texto adicional a la derecha del título (por ejemplo, el paso en ejecución). */
  extra?: ReactNode
  className?: string
}

export function Desplegable({ titulo, children, abierto, alCambiar, extra, className }: Props) {
  const idPanel = useId()
  const [interno, setInterno] = useState(false)
  const estaAbierto = abierto ?? interno
  const alternar = () => {
    const siguiente = !estaAbierto
    setInterno(siguiente)
    alCambiar?.(siguiente)
  }
  return (
    <div className={cn('text-xs', className)}>
      <button
        type="button"
        onClick={alternar}
        aria-expanded={estaAbierto}
        aria-controls={idPanel}
        className="inline-flex items-center gap-1 rounded-md py-0.5 pr-1.5 pl-0.5 font-medium text-texto-suave hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring"
      >
        <ChevronRight className={cn('size-3.5 transition-transform', estaAbierto && 'rotate-90')} aria-hidden />
        <span>{titulo}</span>
        {extra && <span className="ml-1 font-normal">{extra}</span>}
      </button>
      {estaAbierto && (
        <div id={idPanel} className="mt-1">
          {children}
        </div>
      )}
    </div>
  )
}
