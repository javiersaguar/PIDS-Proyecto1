/**
 * Devuelve `valor` con un retardo: solo cambia cuando el valor lleva `ms` sin moverse (para no pedir sugerencias
 * al servidor en cada pulsación).
 */
import { useEffect, useState } from 'react'

export function useValorRetardado<T>(valor: T, ms = 250): T {
  const [retardado, setRetardado] = useState(valor)
  useEffect(() => {
    const id = setTimeout(() => setRetardado(valor), ms)
    return () => clearTimeout(id)
  }, [valor, ms])
  return retardado
}
