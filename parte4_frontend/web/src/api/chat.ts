/**
 * Chat del portal (CONTRATOS.md §5, bloque F2 del BFF):
 *
 *   const motores = useMotores()                                   // GET /api/chat/motores
 *   const { id } = await crearSesion('ollama')                      // POST /api/chat/sesiones
 *   await enviarMensaje(id, '¿Cuántos viajes…?', alRecibir)         // POST …/{id}/mensajes  (SSE)
 *   await pedirAlternativa(id, alRecibir)                           // POST …/{id}/alternativa (SSE)
 *   await cerrarSesion(id)                                          // DELETE /api/chat/sesiones/{id}
 *
 * Los mensajes y la alternativa responden con `text/event-stream` a un POST, así que no vale `EventSource`:
 * se hace `fetch` con la cookie y se lee `response.body` con el parser de `componentes/chat/sse.ts`.
 * Eventos: `paso` (EventoPaso, uno por herramienta ejecutada), `respuesta` (EventoRespuesta, el último) y
 * `error` ({detail}). Los errores HTTP se lanzan como `ErrorApi`, igual que en `api()`; un 401 se lanza tal
 * cual y quien llama (el hook del asistente) lo trata como sesión perdida.
 */
import { useQuery } from '@tanstack/react-query'

import { ErrorApi, api, detalleDe } from './cliente'
import type { EventoPaso, EventoRespuesta, Motor } from './tipos'
import { leerFlujoSse } from '@/componentes/chat/sse'

export const CLAVE_MOTORES = ['chat', 'motores'] as const
const RUTA_SESIONES = '/api/chat/sesiones'

export interface SesionChat {
  id: string
  motor: Motor['id']
}

/** Un evento ya interpretado del flujo SSE de una respuesta. */
export type EventoChat =
  | { tipo: 'paso'; datos: EventoPaso }
  | { tipo: 'respuesta'; datos: EventoRespuesta }
  | { tipo: 'error'; datos: { detail: string } }

export type AlRecibirEvento = (evento: EventoChat) => void

export function useMotores() {
  return useQuery({
    queryKey: CLAVE_MOTORES,
    queryFn: () => api<Motor[]>('/api/chat/motores'),
    staleTime: 60_000,
  })
}

export function crearSesion(motor: Motor['id']): Promise<SesionChat> {
  return api<SesionChat>(RUTA_SESIONES, { method: 'POST', json: { motor } })
}

export async function cerrarSesion(id: string): Promise<void> {
  await api<void>(`${RUTA_SESIONES}/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

/** Envía un mensaje y entrega los eventos según llegan; resuelve cuando el servidor cierra el flujo. */
export function enviarMensaje(id: string, texto: string, alRecibir: AlRecibirEvento, señal?: AbortSignal): Promise<void> {
  return consumirSse(`${RUTA_SESIONES}/${encodeURIComponent(id)}/mensajes`, { texto }, alRecibir, señal)
}

/** Ejecuta la alternativa pendiente de la sesión (la que propuso el último rechazo), con el mismo flujo. */
export function pedirAlternativa(id: string, alRecibir: AlRecibirEvento, señal?: AbortSignal): Promise<void> {
  return consumirSse(`${RUTA_SESIONES}/${encodeURIComponent(id)}/alternativa`, {}, alRecibir, señal)
}

async function leerCuerpo(respuesta: Response): Promise<unknown> {
  const texto = await respuesta.text().catch(() => '')
  if (!texto) return null
  try {
    return JSON.parse(texto) as unknown
  } catch {
    return texto
  }
}

/** Convierte un mensaje SSE del BFF en un `EventoChat`; los tipos desconocidos se ignoran (devuelve null). */
export function interpretarEvento(evento: string, datos: string): EventoChat | null {
  let cuerpo: unknown
  try {
    cuerpo = JSON.parse(datos)
  } catch {
    if (evento === 'error') return { tipo: 'error', datos: { detail: datos || 'Error del asistente' } }
    return { tipo: 'error', datos: { detail: 'El asistente ha enviado una respuesta que no se puede interpretar' } }
  }
  if (evento === 'paso') return { tipo: 'paso', datos: cuerpo as EventoPaso }
  if (evento === 'respuesta') return { tipo: 'respuesta', datos: cuerpo as EventoRespuesta }
  if (evento === 'error') return { tipo: 'error', datos: { detail: detalleDe(cuerpo, 500) } }
  return null
}

async function consumirSse(ruta: string, cuerpo: unknown, alRecibir: AlRecibirEvento, señal?: AbortSignal): Promise<void> {
  let respuesta: Response
  try {
    respuesta = await fetch(ruta, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(cuerpo),
      credentials: 'include',
      signal: señal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ErrorApi(0, 'No se ha podido conectar con el portal', null)
  }
  if (!respuesta.ok) {
    const contenido = await leerCuerpo(respuesta)
    throw new ErrorApi(respuesta.status, detalleDe(contenido, respuesta.status), contenido)
  }
  if (!respuesta.body) {
    throw new ErrorApi(0, 'El asistente no ha devuelto ningún contenido', null)
  }
  await leerFlujoSse(respuesta.body, ({ evento, datos }) => {
    const interpretado = interpretarEvento(evento, datos)
    if (interpretado) alRecibir(interpretado)
  })
}
