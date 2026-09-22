/**
 * Botón fijo de la esquina inferior derecha que abre el panel de TAXI AI desde cualquier página.
 * Con el panel abierto se oculta: el panel ya tiene su X (y Escape), y un segundo botón flotando sobre la página
 * quedaba encima del contenido. Al cerrar el panel vuelve a aparecer y recibe el foco.
 */
import { Sparkles } from 'lucide-react'
import type { Ref } from 'react'

import { cn } from '@/lib/utils'

import { ID_PANEL_ASISTENTE } from './PanelAsistente'

interface Props {
  abierto: boolean
  alPulsar: () => void
  ref?: Ref<HTMLButtonElement>
}

export function BotonTaxiAI({ abierto, alPulsar, ref }: Props) {
  return (
    <button
      ref={ref}
      type="button"
      onClick={alPulsar}
      aria-expanded={abierto}
      aria-controls={ID_PANEL_ASISTENTE}
      aria-label="Abrir TAXI AI, el asistente de datos"
      aria-hidden={abierto}
      tabIndex={abierto ? -1 : undefined}
      className={cn(
        // bottom-40: por encima de la fila baja del grafo (Chatbots, Ollama) y del enlace de abrir de la tabla
        'fixed right-6 bottom-40 z-50 inline-flex h-12 items-center gap-2.5 rounded-full pr-5 pl-4 text-sm font-semibold tracking-wide text-white',
        'bg-[#6d4aff] shadow-[0_14px_36px_-12px_rgba(109,74,255,0.75)] transition-[opacity,background-color,transform] duration-200 ease-out',
        'hover:-translate-y-0.5 hover:bg-[#5b3ae0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6d4aff]',
        abierto && 'pointer-events-none invisible scale-90 opacity-0',
      )}
    >
      <Sparkles className="size-4" aria-hidden />
      TAXI AI
    </button>
  )
}
