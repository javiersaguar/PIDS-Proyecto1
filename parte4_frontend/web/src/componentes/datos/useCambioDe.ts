/**
 * Recuerda el último cambio de un valor entre renders: con qué valor venía y cuál trae. Sirve para decir
 * «+1.234 viajes desde el dato anterior», «nueva hora: 23:00» o para animar solo a partir del segundo dato.
 *
 *   const cambio = useCambioDe(total, `${fuente}|${dia}`)   // null hasta que `total` cambie con la misma clave
 *   const instante = useInstanteDe(cambio?.n)               // cuándo ocurrió (ms), para «hace X s»
 *
 * La `clave` delimita qué se compara: si cambia (otra pestaña, otro día), se empieza de cero sin anotar un cambio.
 * Es el patrón de React de guardar información de renders anteriores: el estado se ajusta durante el render, sin
 * efectos ni parpadeo; la hora del cambio se toma aparte, en un efecto, para que el render siga siendo puro.
 */
import { useEffect, useState } from 'react'

export interface CambioDe<T> {
  anterior: T
  actual: T
  /** Cuántos cambios van con esta clave: sirve de `key` para volver a lanzar una animación. */
  n: number
}

interface Estado<T> {
  clave: string
  valor: T
  cambio: CambioDe<T> | null
}

export function useCambioDe<T>(valor: T, clave = ''): CambioDe<T> | null {
  const [estado, setEstado] = useState<Estado<T>>({ clave, valor, cambio: null })
  if (estado.clave === clave && Object.is(estado.valor, valor)) return estado.cambio
  const cambio = estado.clave === clave ? { anterior: estado.valor, actual: valor, n: (estado.cambio?.n ?? 0) + 1 } : null
  setEstado({ clave, valor, cambio })
  return cambio
}

/** El instante (ms) en que `n` tomó su valor actual; `null` mientras no haya habido ningún cambio. */
export function useInstanteDe(n: number | null | undefined): number | null {
  const [instante, setInstante] = useState<number | null>(null)
  useEffect(() => {
    if (!n) return
    const id = setTimeout(() => setInstante(Date.now()), 0)
    return () => clearTimeout(id)
  }, [n])
  return n ? instante : null
}
