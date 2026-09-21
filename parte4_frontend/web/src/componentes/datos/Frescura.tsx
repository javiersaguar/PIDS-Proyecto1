/**
 * Frescura del tiempo real: semáforo + «hace X s» que avanza en el cliente desde que llegó el dato.
 * `segundos` es la antigüedad que calculó el BFF al responder; a eso se le suma lo que ha pasado desde
 * entonces (`actualizadoEn`, el `dataUpdatedAt` de la consulta).
 */
import { Semaforo } from '@/componentes/graficos/Semaforo'
import { nivelFrescura, TEXTO_FRESCURA } from '@/componentes/graficos/frescura'
import { cn } from '@/lib/utils'

import { describirAntiguedad, formatearFechaHora } from './formato'
import { useSegundosDesde } from './useAhora'

interface Props {
  /** Antigüedad de la última escritura de tiempo real cuando respondió el BFF; `null` si no hay dato. */
  segundos: number | null | undefined
  /** Instante de esa última escritura (ISO), para mostrarlo completo. */
  instante?: string | null
  /** Cuándo llegó la respuesta (ms desde la época), para que el contador avance. */
  actualizadoEn?: number
  /** `grande` para las tarjetas KPI; `linea` para textos en línea. */
  variante?: 'grande' | 'linea'
  className?: string
}

export function Frescura({ segundos, instante, actualizadoEn, variante = 'linea', className }: Props) {
  const transcurridos = useSegundosDesde(actualizadoEn)
  const actuales = segundos == null ? null : segundos + (transcurridos ?? 0)
  const nivel = nivelFrescura(actuales)
  const antiguedad = describirAntiguedad(actuales)

  if (variante === 'grande') {
    return (
      <div className={cn('space-y-1', className)}>
        <p className={cn('cifra text-2xl leading-tight font-semibold', nivel === 'ok' ? 'text-ok' : nivel === 'aviso' ? 'text-aviso' : 'text-peligro')}>
          {actuales == null ? 'Sin dato' : antiguedad}
        </p>
        <Semaforo nivel={nivel} etiqueta={TEXTO_FRESCURA[nivel]} tamano="sm" className="text-xs" />
        {instante && <p className="text-xs text-texto-suave">Última escritura: {formatearFechaHora(instante)}</p>}
      </div>
    )
  }

  return (
    <Semaforo
      nivel={nivel}
      className={className}
      etiqueta={
        <span>
          {TEXTO_FRESCURA[nivel]}
          <span className="cifra font-normal text-texto-suave"> · {antiguedad}</span>
        </span>
      }
    />
  )
}
