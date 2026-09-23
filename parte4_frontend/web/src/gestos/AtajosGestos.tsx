/**
 * Los gestos que manejan el portal y no el chat:
 *   🤘 abre TAXI AI y ✊ lo cierra, desde cualquier página;
 *   ✋ pasa a la siguiente sección del menú (Panel → Explorador → … → Observabilidad → Panel). TAXI AI no es una
 *      sección: es el panel de la derecha, así que ✋ no pasa por él; si está abierto, sigue abierto al cambiar de
 *      sección y la conversación no se pierde.
 * Un gesto del chat (otra pregunta, cambiar de motor, leer) con el panel cerrado lo abre, y el chat lo atiende en cuanto
 * tiene sesión (`useGestosChat`).
 */
import { useLocation, useNavigate } from 'react-router'

import { seccionSiguiente } from '@/componentes/shell/navegacion'

import { useAlGesto } from './contexto'
import { GESTOS } from './tabla'

interface Props {
  abierto: boolean
  alAbrir: () => void
  alCerrar: () => void
}

export function AtajosGestos({ abierto, alAbrir, alCerrar }: Props) {
  const navegar = useNavigate()
  const { pathname } = useLocation()
  useAlGesto(({ gesto }) => {
    const accion = GESTOS[gesto].accion
    if (accion === 'cerrar') alCerrar()
    else if (accion === 'seccion') void navegar(seccionSiguiente(pathname))
    else if (!abierto) alAbrir()
  })
  return null
}
