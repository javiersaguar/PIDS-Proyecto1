/**
 * Botón fijo de la esquina inferior derecha que abre y cierra el panel de TAXI AI desde cualquier página.
 * Con el panel abierto se desplaza a su izquierda (en pantallas medianas y grandes) para no tapar el cuadro
 * de texto, y pasa a «cerrar»; en pantallas pequeñas el panel ocupa todo el ancho y basta con su propia X.
 */
import { Sparkles, X } from 'lucide-react'
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
      aria-label={abierto ? 'Cerrar TAXI AI' : 'Abrir TAXI AI, el asistente de datos'}
      className={cn(
        'fixed bottom-6 z-50 inline-flex h-12 items-center gap-2.5 rounded-full pr-5 pl-4 text-sm font-semibold tracking-wide text-white',
        'bg-[#6d4aff] shadow-[0_14px_36px_-12px_rgba(109,74,255,0.75)] transition-[right,background-color,transform] duration-300 ease-out',
        'hover:-translate-y-0.5 hover:bg-[#5b3ae0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6d4aff]',
        // 31,5 rem = los 30 rem del panel (PanelAsistente) más el margen de 1,5 rem
        abierto ? 'right-[31.5rem] max-md:hidden' : 'right-6',
      )}
    >
      {abierto ? <X className="size-4" aria-hidden /> : <Sparkles className="size-4" aria-hidden />}
      TAXI AI
    </button>
  )
}
