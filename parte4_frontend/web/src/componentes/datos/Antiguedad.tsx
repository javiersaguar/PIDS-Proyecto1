/**
 * «Actualizado hace 12 s»: texto que avanza cada segundo en el cliente. Es un componente aparte para que el
 * reloj solo re-renderice este texto y no la página entera (ni sus gráficos).
 */
import { cn } from '@/lib/utils'

import { describirAntiguedad } from './formato'
import { useSegundosDesde } from './useAhora'

interface Props {
  /** Instante de referencia en ms desde la época (por ejemplo, `dataUpdatedAt` de una consulta). */
  instante: number | null | undefined
  prefijo?: string
  sufijo?: string
  className?: string
}

export function Antiguedad({ instante, prefijo = 'Actualizado', sufijo, className }: Props) {
  const segundos = useSegundosDesde(instante || null)
  if (segundos === null) return null
  return (
    <span className={cn('cifra', className)}>
      {prefijo} {describirAntiguedad(segundos)}
      {sufijo && ` ${sufijo}`}
    </span>
  )
}
