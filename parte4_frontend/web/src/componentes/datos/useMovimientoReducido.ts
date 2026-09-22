/**
 * ¿El usuario ha pedido menos movimiento (`prefers-reduced-motion: reduce`)? Las animaciones de CSS lo respetan
 * solas con la consulta de medios; las que se hacen en JavaScript o con SMIL (`animateMotion`) tienen que
 * preguntarlo aquí. Sin `matchMedia` (jsdom, navegadores antiguos) se asume que el movimiento está permitido.
 */
import { useEffect, useState } from 'react'

const CONSULTA = '(prefers-reduced-motion: reduce)'

function consultar(): MediaQueryList | null {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(CONSULTA) : null
}

export function useMovimientoReducido(): boolean {
  const [reducido, setReducido] = useState(() => consultar()?.matches ?? false)
  useEffect(() => {
    const medios = consultar()
    if (!medios || typeof medios.addEventListener !== 'function') return
    const alCambiar = (evento: MediaQueryListEvent) => setReducido(evento.matches)
    medios.addEventListener('change', alCambiar)
    return () => medios.removeEventListener('change', alCambiar)
  }, [])
  return reducido
}
