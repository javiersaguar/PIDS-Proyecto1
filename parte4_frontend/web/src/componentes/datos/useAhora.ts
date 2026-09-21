/**
 * Reloj que avanza cada `intervaloMs` (por defecto, cada segundo) para los textos «hace X s».
 * Solo re-renderiza a quien lo usa: el resto de la página no se entera.
 */
import { useEffect, useState } from 'react'

export function useAhora(intervaloMs = 1000): number {
  const [ahora, setAhora] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), intervaloMs)
    return () => clearInterval(id)
  }, [intervaloMs])
  return ahora
}

/**
 * Segundos transcurridos desde `instante` (ms desde la época), avanzando en cliente.
 * `null` si no hay instante (por ejemplo, la consulta aún no ha respondido).
 */
export function useSegundosDesde(instante: number | null | undefined, intervaloMs = 1000): number | null {
  const ahora = useAhora(intervaloMs)
  if (!instante) return null
  return Math.max(0, (ahora - instante) / 1000)
}
