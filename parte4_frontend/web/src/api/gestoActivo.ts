/**
 * El último gesto reconocido, para que el grafo lo ilumine unos segundos: si entró en la plataforma, por la API de
 * captura y la cola de Redpanda hasta los chatbots; si se quedó en el navegador (la demostración), solo en los
 * chatbots. Lo marca el proveedor de gestos (`gestos/ContextoGestos.tsx`); `useActividad` lo lee.
 */
import { useSyncExternalStore } from 'react'

import type { Gesto } from '@/gestos/tabla'

export interface GestoReciente {
  gesto: Gesto
  enPlataforma: boolean
  instante: number
}

const oyentes = new Set<() => void>()
let actual: GestoReciente | null = null

export function marcarGesto(gesto: Gesto, enPlataforma: boolean, instante = Date.now()): void {
  actual = { gesto, enPlataforma, instante }
  oyentes.forEach((oyente) => oyente())
}

export function gestoReciente(): GestoReciente | null {
  return actual
}

export function useGestoReciente(): GestoReciente | null {
  return useSyncExternalStore(
    (oyente) => {
      oyentes.add(oyente)
      return () => oyentes.delete(oyente)
    },
    gestoReciente,
    () => null,
  )
}
