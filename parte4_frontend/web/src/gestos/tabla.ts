/**
 * Qué hace cada gesto de la parte 1: la tabla de `config/gestos.json`, la misma que leen los dos chatbots de Chainlit
 * (`parte3_chatbot/gestos.py`). Aquí se usan las seis acciones; en Chainlit solo ✌️ (otra pregunta).
 */
import tabla from '../../../../config/gestos.json'

export type Gesto = 'ok' | 'paper' | 'rock' | 'rockandroll' | 'scissors' | 'thumbsup'
export type Accion = 'siguiente' | 'motor' | 'seccion' | 'leer' | 'abrir' | 'cerrar'

export interface DatosGesto {
  emoji: string
  accion: Accion
  titulo: string
  texto: string
}

export const GESTOS = tabla.gestos as Record<Gesto, DatosGesto>
/** En el orden de la tabla: otra pregunta, cambiar de motor, siguiente sección, leer, abrir y cerrar. */
export const LISTA_GESTOS = Object.keys(GESTOS) as Gesto[]
export const PREGUNTAS_GESTO: readonly string[] = tabla.preguntas
export const CONFIANZA_MINIMA: number = tabla.confianza_minima
/** Predicciones seguidas del mismo gesto para darlo por hecho (una cada `MS_ENTRE_MUESTRAS`). */
export const ESTABILIDAD: number = tabla.estabilidad
export const REPETIR_CADA_MS: number = tabla.repetir_cada_s * 1000
/** El ritmo de la demo de Windows: una predicción cada 0,25 s llega al filtro (unos 1 s sosteniendo el gesto). */
export const MS_ENTRE_MUESTRAS = 250

export function esGesto(valor: unknown): valor is Gesto {
  return typeof valor === 'string' && valor in GESTOS
}
