/**
 * Cifras que se mueven hacia su valor nuevo en vez de saltar: cuando el panel o el tiempo real se refrescan y
 * un total cambia, el número recorre el camino en unos 700 ms (suavizado al final). En el primer render se
 * muestra el valor tal cual, y con `prefers-reduced-motion` no hay recorrido.
 *
 *   const total = useNumeroAnimado(panel.total)          // number | null, listo para formatearEntero
 *   const barras = useValoresAnimados(serie)              // un array, cada valor animado por su posición
 */
import { useEffect, useRef, useState } from 'react'

import { useMovimientoReducido } from './useMovimientoReducido'

export const DURACION_ANIMACION_MS = 700
const SEPARADOR = '|'

/** Suavizado cúbico de salida: arranca rápido y frena al llegar. */
export function suavizar(progreso: number): number {
  const p = Math.min(1, Math.max(0, progreso))
  return 1 - (1 - p) ** 3
}

/** El valor intermedio entre `desde` y `hasta` en el instante `progreso` (0–1) del recorrido. */
export function interpolar(desde: number, hasta: number, progreso: number): number {
  return desde + (hasta - desde) * suavizar(progreso)
}

// El efecto depende de la firma (texto) y no del array: quien llama suele construir un array nuevo en cada
// render y, si el efecto se reiniciara con cada uno, cancelaría la animación en su primer fotograma.
function firmaDe(valores: readonly number[]): string {
  return valores.map(String).join(SEPARADOR)
}

function deFirma(firma: string): number[] {
  return firma === '' ? [] : firma.split(SEPARADOR).map(Number)
}

/**
 * Anima un array de números posición a posición. Si cambia la longitud (aparece una hora nueva, desaparece un
 * barrio) no hay recorrido: se salta al array nuevo, porque no hay correspondencia entre las posiciones.
 */
export function useValoresAnimados(valores: readonly number[], duracionMs = DURACION_ANIMACION_MS): readonly number[] {
  const reducido = useMovimientoReducido()
  const firma = firmaDe(valores)
  const [mostrados, setMostrados] = useState<readonly number[]>(valores)
  const anterior = useRef(firma)

  useEffect(() => {
    const desde = deFirma(anterior.current)
    const hasta = deFirma(firma)
    anterior.current = firma
    if (desde.length === hasta.length && desde.every((valor, indice) => valor === hasta[indice])) return
    if (reducido || desde.length !== hasta.length || typeof requestAnimationFrame !== 'function') {
      setMostrados(hasta)
      return
    }
    const inicio = performance.now()
    let peticion = 0
    const paso = (ahora: number) => {
      const progreso = (ahora - inicio) / duracionMs
      if (progreso >= 1) {
        setMostrados(hasta)
        return
      }
      setMostrados(hasta.map((valor, indice) => interpolar(desde[indice], valor, progreso)))
      peticion = requestAnimationFrame(paso)
    }
    peticion = requestAnimationFrame(paso)
    return () => {
      if (typeof cancelAnimationFrame === 'function') cancelAnimationFrame(peticion)
    }
  }, [firma, duracionMs, reducido])

  return mostrados
}

/** Un solo número; `null` (sin dato) se muestra en el acto, sin recorrido. */
export function useNumeroAnimado(valor: number | null | undefined, duracionMs = DURACION_ANIMACION_MS): number | null {
  const lista = useValoresAnimados(valor == null || !Number.isFinite(valor) ? [] : [valor], duracionMs)
  return lista.length ? lista[0] : null
}
