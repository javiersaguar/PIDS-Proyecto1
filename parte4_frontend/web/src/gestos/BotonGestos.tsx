/**
 * El botón de los gestos: una pastilla como la de TAXI AI, fija abajo a la izquierda. En la web pública va encima del
 * aviso de modo («En vivo» / «Demostración») y sube o baja cuando ese aviso se despliega o se pliega; en el portal del
 * equipo, donde no hay aviso, en el mismo sitio. Enciende la cámara y el reconocimiento, o los apaga, y un punto dice
 * en qué estado están.
 */
import { Hand } from 'lucide-react'
import { useEffect, useState } from 'react'

import { cn } from '@/lib/utils'

import { useGestos } from './contexto'

const ESTADOS = {
  apagada: { texto: 'apagados', punto: 'bg-white/60' },
  cargando: { texto: 'preparando la cámara', punto: 'bg-amber-300 animate-pulse' },
  activa: { texto: 'cámara activa', punto: 'bg-emerald-400' },
  error: { texto: 'sin cámara', punto: 'bg-red-400' },
} as const

/** Alto del aviso de modo de la web pública (0 si no lo hay), siguiéndolo cuando se pliega o se despliega. */
function useAltoAviso(): number {
  const [alto, setAlto] = useState(0)
  useEffect(() => {
    const aviso = document.querySelector<HTMLElement>('[data-aviso-modo]')
    if (!aviso || typeof ResizeObserver === 'undefined') return
    const observador = new ResizeObserver(() => setAlto(aviso.offsetHeight))
    observador.observe(aviso)
    return () => observador.disconnect()
  }, [])
  return alto
}

export function BotonGestos() {
  const { estado, activar, desactivar } = useGestos()
  const altoAviso = useAltoAviso()
  const encendido = estado === 'activa' || estado === 'cargando'
  const { texto, punto } = ESTADOS[estado]
  return (
    <button
      type="button"
      aria-pressed={encendido}
      aria-label={`Gestos: ${texto}`}
      onClick={encendido ? desactivar : activar}
      title={encendido ? 'Apagar la cámara y los gestos' : 'Manejar el portal con gestos de la mano (la imagen no sale del navegador)'}
      // 4,5 rem: por encima del pie del menú («Cerrar sesión»), como el aviso de modo
      style={{ bottom: altoAviso ? `calc(4.5rem + ${altoAviso}px + 0.5rem)` : '4.5rem' }}
      className={cn(
        'fixed left-3 z-50 inline-flex h-9 items-center gap-2 rounded-full pr-3.5 pl-3 text-[13px] font-semibold tracking-wide text-white',
        'shadow-[0_14px_36px_-12px_rgba(109,74,255,0.75)] transition-[background-color,transform,bottom] duration-200 ease-out motion-reduce:transition-none',
        'hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6d4aff]',
        encendido ? 'bg-[#5b3ae0] ring-2 ring-[#c4b5fd]' : 'bg-[#6d4aff] hover:bg-[#5b3ae0]',
      )}
    >
      <Hand className="size-3.5" aria-hidden />
      Gestos
      <span className={cn('size-1.5 rounded-full', punto)} aria-hidden />
    </button>
  )
}
