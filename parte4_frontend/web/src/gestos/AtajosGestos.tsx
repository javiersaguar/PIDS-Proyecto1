/**
 * 🤘 abre TAXI AI y ✊ lo cierra, desde cualquier página. Un gesto del chat (confirmar, parar, otra pregunta, leer)
 * con el panel cerrado lo abre, y el chat lo atiende en cuanto tiene sesión (`useGestosChat`).
 */
import { useAlGesto } from './contexto'
import { GESTOS } from './tabla'

interface Props {
  abierto: boolean
  alAbrir: () => void
  alCerrar: () => void
}

export function AtajosGestos({ abierto, alAbrir, alCerrar }: Props) {
  useAlGesto(({ gesto }) => {
    const accion = GESTOS[gesto].accion
    if (accion === 'cerrar') alCerrar()
    else if (!abierto && accion !== 'cancelar') alAbrir()
  })
  return null
}
