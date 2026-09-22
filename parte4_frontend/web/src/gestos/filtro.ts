/**
 * Cuándo una predicción es un gesto de verdad: el mismo criterio que `EmisorGestos.observar` de la demo de Windows
 * (`integracion/cliente_gestos.py`). El gesto tiene que repetirse `ESTABILIDAD` predicciones seguidas con confianza
 * suficiente, y el mismo gesto no vuelve a contar hasta pasados 3 s. Así una mano que pasa por delante de la cámara
 * o un cambio de postura no disparan nada.
 */
import { CONFIANZA_MINIMA, ESTABILIDAD, REPETIR_CADA_MS, type Gesto } from './tabla'

export class FiltroGestos {
  private candidato: Gesto | null = null
  private racha = 0
  private ultimo: Gesto | null = null
  private instanteUltimo = -Infinity
  private readonly estabilidad: number
  private readonly confianzaMinima: number
  private readonly repetirCadaMs: number

  constructor(estabilidad = ESTABILIDAD, confianzaMinima = CONFIANZA_MINIMA, repetirCadaMs = REPETIR_CADA_MS) {
    this.estabilidad = estabilidad
    this.confianzaMinima = confianzaMinima
    this.repetirCadaMs = repetirCadaMs
  }

  /** Una predicción (`null` si no hay mano). Devuelve el gesto cuando queda confirmado; si no, `null`. */
  observar(gesto: Gesto | null, confianza: number, ahoraMs: number): Gesto | null {
    if (gesto === null || confianza < this.confianzaMinima) {
      this.candidato = null
      this.racha = 0
      return null
    }
    this.racha = gesto === this.candidato ? this.racha + 1 : 1
    this.candidato = gesto
    const repetido = gesto === this.ultimo && ahoraMs - this.instanteUltimo < this.repetirCadaMs
    if (this.racha < this.estabilidad || repetido) return null
    this.ultimo = gesto
    this.instanteUltimo = ahoraMs
    return gesto
  }

  /** Progreso del gesto que se está sosteniendo (0 a 1), para la barra de la tarjeta. */
  progreso(): number {
    return this.candidato ? Math.min(1, this.racha / this.estabilidad) : 0
  }
}
