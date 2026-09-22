/**
 * Los dos botones de zoom del grafo: pequeños y casi transparentes en la esquina superior derecha, para no tapar
 * nada; se ven del todo al pasar por encima o con el foco del teclado.
 */
import { ZoomIn, ZoomOut } from 'lucide-react'

import { cn } from '@/lib/utils'

import { ZOOM_MAXIMO, ZOOM_MINIMO } from './zoom'

interface Props {
  zoom: number
  alAcercar: () => void
  alAlejar: () => void
  className?: string
}

const BOTON =
  'flex size-8 items-center justify-center rounded-lg border border-slate-200/70 bg-white/70 text-slate-600 shadow-sm backdrop-blur ' +
  'transition hover:bg-white hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-[#60a5fa] disabled:cursor-not-allowed disabled:opacity-40'

export function ControlesZoom({ zoom, alAcercar, alAlejar, className }: Props) {
  return (
    <div
      role="group"
      aria-label="Zoom del grafo"
      className={cn('absolute top-3 right-3 z-10 flex flex-col gap-1 opacity-45 transition-opacity hover:opacity-100 focus-within:opacity-100', className)}
    >
      <button type="button" className={BOTON} onClick={alAcercar} disabled={zoom >= ZOOM_MAXIMO} aria-label="Acercar" title="Acercar">
        <ZoomIn className="size-4" aria-hidden />
      </button>
      <button type="button" className={BOTON} onClick={alAlejar} disabled={zoom <= ZOOM_MINIMO} aria-label="Alejar" title="Alejar">
        <ZoomOut className="size-4" aria-hidden />
      </button>
    </div>
  )
}
