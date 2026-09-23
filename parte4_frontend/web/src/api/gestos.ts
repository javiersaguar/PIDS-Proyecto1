/**
 * Gestos de la parte 1 entre el portal y la plataforma (`bff/rutas/gestos.py`):
 *
 *   await enviarGesto({gesto: 'thumbsup', confianza: 0.97, dispositivo})   // POST /api/gestos -> {enviado}
 *   await escucharGestos(alRecibir, señal)                                 // GET /api/gestos/stream (SSE)
 *   const { pregunta } = await pedirPregunta(anterior)                     // GET /api/gestos/pregunta (la de ✌️)
 *
 * El gesto que reconoce el navegador va a la API de captura (cliente `gestos`) y de ahí a la cola de Redpanda, igual
 * que los de la demo de Windows; los que entran por la plataforma llegan aquí. Se usa `fetch` (no `EventSource`)
 * para que la demostración pública, que responde a `fetch`, pueda decir que no hay flujo.
 */
import { leerFlujoSse } from '@/componentes/chat/sse'

import { ErrorApi, api } from './cliente'
import type { Gesto } from '@/gestos/tabla'

export interface GestoEnviado {
  gesto: Gesto
  confianza: number
  /** `portal-…`: identifica esta pestaña, para no repetir el gesto cuando vuelve por el flujo. */
  dispositivo: string
}

export interface GestoRecibido {
  gesto: string
  confianza: number
  dispositivo: string | null
  instante: string | null
}

export interface ResultadoEnvio {
  enviado: boolean
  /** Solo en la demostración: el gesto se queda en el navegador. */
  demostracion?: boolean
}

/** ✌️: una pregunta al azar hecha con las plantillas de `config/gestos.json` (en la demostración, una grabada). */
export function pedirPregunta(anterior: string | null): Promise<{ pregunta: string }> {
  const consulta = anterior ? `?anterior=${encodeURIComponent(anterior)}` : ''
  return api<{ pregunta: string }>(`/api/gestos/pregunta${consulta}`)
}

export function enviarGesto(gesto: GestoEnviado): Promise<ResultadoEnvio> {
  return api<ResultadoEnvio>('/api/gestos', { method: 'POST', json: gesto })
}

/**
 * Entrega los gestos de la plataforma según llegan; resuelve cuando el servidor cierra el flujo. Un error HTTP (404
 * en la demostración, 503 sin clave de gestos) se lanza como `ErrorApi` y quien escucha decide si reintenta.
 */
export async function escucharGestos(alRecibir: (gesto: GestoRecibido) => void, señal: AbortSignal): Promise<void> {
  const respuesta = await fetch('/api/gestos/stream', {
    headers: { Accept: 'text/event-stream' },
    credentials: 'include',
    signal: señal,
  })
  if (!respuesta.ok || !respuesta.body) {
    throw new ErrorApi(respuesta.status, `El flujo de gestos no está disponible (HTTP ${respuesta.status})`, null)
  }
  await leerFlujoSse(respuesta.body, ({ evento, datos }) => {
    if (evento !== 'gesto') return
    try {
      alRecibir(JSON.parse(datos) as GestoRecibido)
    } catch {
      // un evento que no es JSON no es un gesto
    }
  })
}
