/**
 * Indicador «En vivo» de una página que se refresca sola: un punto que late mientras la plataforma trabaja, qué
 * está pasando (carga, simulación, Spark publicando) y cuándo llegó el último dato y cuándo llega el siguiente.
 * Es la misma información que la barra del grafo, en pequeño.
 */
import { useSegundosDesde } from './useAhora'
import { cn } from '@/lib/utils'

interface Props {
  /** Hay algún proceso en marcha (el punto late en verde). */
  activo: boolean
  /** Qué está pasando, en una frase corta. */
  texto: string
  /** `dataUpdatedAt` de la consulta que alimenta la página. */
  actualizadoEn?: number
  /** Cada cuánto se refresca la página ahora mismo, para decir cuándo llega el siguiente dato. */
  intervaloMs?: number
  /** La consulta está en vuelo. */
  refrescando?: boolean
  className?: string
}

function describir(segundos: number | null, intervaloMs: number | undefined, refrescando: boolean | undefined): string | null {
  if (refrescando) return 'actualizando…'
  if (segundos == null) return null
  const hace = `hace ${Math.floor(segundos)} s`
  if (!intervaloMs) return `actualizado ${hace}`
  const faltan = Math.max(0, Math.ceil(intervaloMs / 1000 - segundos))
  return `actualizado ${hace} · siguiente en ${faltan} s`
}

export function EnVivo({ activo, texto, actualizadoEn, intervaloMs, refrescando, className }: Props) {
  const segundos = useSegundosDesde(actualizadoEn)
  const detalle = describir(segundos, intervaloMs, refrescando)
  return (
    <div
      role="status"
      aria-label="Actividad de la plataforma"
      className={cn(
        'flex flex-wrap items-center gap-x-3 gap-y-1 rounded-full border bg-white/90 px-3 py-1.5 text-xs shadow-[0_1px_2px_rgba(15,23,42,0.04)]',
        activo ? 'border-emerald-200 text-emerald-800' : 'border-slate-200 text-slate-500',
        className,
      )}
    >
      <span className="flex items-center gap-2 font-medium">
        <span className="relative flex size-2.5 shrink-0" aria-hidden>
          {activo && <span className="punto-vivo absolute inset-0 rounded-full bg-emerald-400/60" />}
          <span className={cn('relative size-2.5 rounded-full', activo ? 'bg-emerald-500' : 'bg-slate-300')} />
        </span>
        {texto}
      </span>
      {detalle && <span className="cifra text-slate-400">{detalle}</span>}
    </div>
  )
}
