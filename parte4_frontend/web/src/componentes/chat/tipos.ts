/**
 * Mensajes del hilo del asistente, tal y como los mantiene `useConversacion` y los pinta `Burbuja`.
 */
import type { EventoPaso, EventoRespuesta } from '@/api/tipos'

export interface MensajeUsuario {
  id: string
  rol: 'usuario'
  texto: string
}

export interface MensajeAsistente {
  id: string
  rol: 'asistente'
  /** Markdown de la respuesta (vacío mientras llega). */
  texto: string
  /** Herramientas ejecutadas, en el orden en que llegan por SSE. */
  pasos: EventoPaso[]
  /** El evento `respuesta` completo, cuando ha llegado. */
  respuesta: EventoRespuesta | null
  /** Aún se está recibiendo (indicador de escritura, pasos en directo). */
  enCurso: boolean
  /** Error del flujo o del servidor (evento `error`, red, sesión caducada…). */
  error: string | null
  /** Qué hizo el usuario con la alternativa propuesta, si la hubo. */
  alternativaResuelta: 'aceptada' | 'cancelada' | null
  /** Mensaje generado por el propio portal («consulta cancelada»), no por el agente. */
  local?: boolean
}

export type MensajeChat = MensajeUsuario | MensajeAsistente

export function esAsistente(mensaje: MensajeChat): mensaje is MensajeAsistente {
  return mensaje.rol === 'asistente'
}

/** Un rechazo del filtro de privacidad: el agente encabeza la respuesta con el candado. */
export function esRechazo(mensaje: MensajeAsistente): boolean {
  return mensaje.texto.includes('🔒')
}

/** Texto en español para el campo `bloqueo` de `EventoRespuesta` (qué barrera actuó en el turno). */
export const TEXTO_BLOQUEO: Record<string, string> = {
  filtro_previo: 'Filtro previo: rechazada sin pasar por el modelo',
  sin_datos: 'Sin datos para esa consulta',
  todo_enmascarado: 'Todos los grupos enmascarados: respuesta sin el modelo',
  cifras_no_verificadas: 'Cifras no verificadas: se sustituyó la respuesta del modelo por los datos',
  sin_terminar: 'El modelo no terminó la respuesta',
}
