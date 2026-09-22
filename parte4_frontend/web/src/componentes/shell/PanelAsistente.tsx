/**
 * Panel de TAXI AI: entra desde el borde derecho al pulsar el botón y se esconde al cerrarlo, sin cambiar de
 * ruta. No es modal: la página sigue usable detrás y no hay fondo oscuro.
 *
 * El chat se monta la primera vez que se abre (así no se abre una sesión en el BFF a quien no lo usa) y se
 * queda montado mientras el panel está cerrado: la conversación sigue donde estaba. Cerrado, el panel queda
 * fuera de la pantalla, `aria-hidden` e `inert`, para que no reciba foco ni lo lean los lectores de pantalla.
 * Escape lo cierra; al abrir, el foco va al cuadro de texto (o al propio panel si aún no se puede escribir), y
 * al cerrar vuelve al botón.
 */
import { useEffect, useRef, useState, type RefObject } from 'react'

import { cn } from '@/lib/utils'
import { Asistente } from '@/paginas/asistente/Asistente'

export const ID_PANEL_ASISTENTE = 'panel-taxi-ai'

interface Props {
  abierto: boolean
  alCerrar: () => void
  /** El botón «TAXI AI», al que vuelve el foco al cerrar. */
  botonRef: RefObject<HTMLButtonElement | null>
}

export function PanelAsistente({ abierto, alCerrar, botonRef }: Props) {
  const panelRef = useRef<HTMLElement>(null)
  const [montado, setMontado] = useState(abierto)
  const estabaAbierto = useRef(abierto)
  // Se monta la primera vez que se abre y no se vuelve a desmontar (estado derivado de la prop, ajustado en el render).
  if (abierto && !montado) setMontado(true)

  // Foco: al abrir, al cuadro de texto; al cerrar, de vuelta al botón (solo si el foco estaba dentro del panel).
  useEffect(() => {
    const panel = panelRef.current
    if (!panel) return
    if (abierto && !estabaAbierto.current) {
      const marco = requestAnimationFrame(() => {
        const entrada = panel.querySelector<HTMLTextAreaElement>('textarea:not(:disabled)')
        ;(entrada ?? panel).focus()
      })
      estabaAbierto.current = true
      return () => cancelAnimationFrame(marco)
    }
    if (!abierto && estabaAbierto.current) {
      estabaAbierto.current = false
      if (panel.contains(document.activeElement)) botonRef.current?.focus()
    }
  }, [abierto, botonRef])

  useEffect(() => {
    if (!abierto) return
    const alTeclear = (evento: KeyboardEvent) => {
      if (evento.key === 'Escape' && !evento.defaultPrevented) alCerrar()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [abierto, alCerrar])

  return (
    <aside
      ref={panelRef}
      id={ID_PANEL_ASISTENTE}
      aria-label="TAXI AI, asistente de datos"
      aria-hidden={!abierto}
      inert={!abierto}
      tabIndex={-1}
      className={cn(
        // w-[min(100vw,30rem)]: 30 rem es también la distancia a la que se desplaza el botón (BotonTaxiAI)
        'fixed inset-y-0 right-0 z-40 flex w-[min(100vw,30rem)] flex-col border-l border-[#eceaf3] bg-white outline-none',
        'shadow-[-24px_0_60px_-30px_rgba(15,23,42,0.35)] transition-transform duration-300 ease-out motion-reduce:transition-none',
        abierto ? 'translate-x-0' : 'translate-x-full',
      )}
    >
      {montado && <Asistente alCerrar={alCerrar} />}
    </aside>
  )
}
