/**
 * Los gestos manejan TAXI AI desde cualquier página. Sin cámara en jsdom, los gestos llegan por el flujo de la
 * plataforma (`/api/gestos/stream`, el camino de la demo de Windows), que actúa igual que la cámara del navegador.
 */
import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { EventoRespuesta, Motor } from '@/api/tipos'
import { ID_PANEL_ASISTENTE } from '@/componentes/shell/PanelAsistente'
import { cuerpoEnviado, renderizarRutas, simularApi } from '@/pruebas/utilidades'

import { DISPOSITIVO } from './contexto'
import { PREGUNTAS_GESTO } from './tabla'
import { textoParaLeer } from './voz'

const MOTORES: Motor[] = [
  { id: 'ollama', nombre: 'Ollama', modelo: 'llama3.1:8b', disponible: true, descripcion: 'Agente local con Ollama' },
]
const RECHAZO: EventoRespuesta = {
  respuesta: 'No puedo darte un viaje concreto.', bloqueo: 'filtro_previo', pasos_llm: 0, segundos: 0.01, tokens: 0,
  alternativa: { nivel: 'hora_zona', desde: '2020-01-15T03:00:00', hasta: '2020-01-15T04:00:00', zona_origen: 230 },
  alternativa_descripcion: 'viajes por hora desde Times Sq (zona 230) el 15/01/2020 de 03:00 a 04:00', fuentes: [],
}

function flujoSse() {
  let controlador!: ReadableStreamDefaultController<Uint8Array>
  const flujo = new ReadableStream<Uint8Array>({ start: (c) => { controlador = c } })
  const codificador = new TextEncoder()
  return {
    respuesta: new Response(flujo, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
    emitir(evento: string, datos: unknown) {
      controlador.enqueue(codificador.encode(`event: ${evento}\r\ndata: ${JSON.stringify(datos)}\r\n\r\n`))
    },
    cerrar: () => controlador.close(),
  }
}

const gesto = (nombre: string, dispositivo = 'PORTATIL-WINDOWS') =>
  ({ gesto: nombre, confianza: 0.97, dispositivo, instante: '2026-09-22T18:00:00+00:00' })
const panel = () => document.getElementById(ID_PANEL_ASISTENTE)!

describe('gestos de la parte 1 en TAXI AI', () => {
  it('✌️ abre el asistente y pregunta, 👍 confirma la alternativa, el propio gesto no se repite y ✊ lo cierra', async () => {
    const gestos = flujoSse()
    const turno = flujoSse()
    const alternativa = flujoSse()
    const espia = simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/gestos/stream': () => gestos.respuesta,
      'GET /api/chat/motores': MOTORES,
      'POST /api/chat/sesiones': { id: 'ses-1', motor: 'ollama' },
      'DELETE /api/chat/sesiones/ses-1': { status: 204 },
      'POST /api/chat/sesiones/ses-1/mensajes': () => turno.respuesta,
      'POST /api/chat/sesiones/ses-1/alternativa': () => alternativa.respuesta,
    })
    renderizarRutas('/no-existe')
    await waitFor(() => expect(espia.mock.calls.some(([url]) => String(url).endsWith('/api/gestos/stream'))).toBe(true))
    expect(panel()).toHaveAttribute('aria-hidden', 'true')

    gestos.emitir('gesto', gesto('scissors'))
    await waitFor(() => expect(panel()).toHaveAttribute('aria-hidden', 'false'))
    await waitFor(() => {
      const indice = espia.mock.calls.findIndex(([url]) => String(url).endsWith('/mensajes'))
      expect(indice).toBeGreaterThanOrEqual(0)
      expect(cuerpoEnviado(espia, indice)).toEqual({ texto: PREGUNTAS_GESTO[0] })
    })
    turno.emitir('respuesta', RECHAZO)
    turno.cerrar()
    const hilo = await screen.findByRole('log', { name: 'Conversación con el asistente' })
    await within(hilo).findByRole('button', { name: '✅ Consultar la alternativa' })

    gestos.emitir('gesto', gesto('thumbsup', DISPOSITIVO))            // el que hizo esta pestaña: ya se atendió
    gestos.emitir('gesto', { ...gesto('thumbsup'), confianza: 0.4 })  // dudoso
    await new Promise((r) => setTimeout(r, 50))
    expect(espia.mock.calls.some(([url]) => String(url).endsWith('/alternativa'))).toBe(false)

    gestos.emitir('gesto', gesto('thumbsup'))
    await waitFor(() => expect(espia.mock.calls.some(([url]) => String(url).endsWith('/alternativa'))).toBe(true))
    expect(within(hilo).getByText(/✅ Consultar la alternativa: viajes por hora/)).toBeInTheDocument()
    alternativa.emitir('respuesta', { ...RECHAZO, respuesta: 'Entre las 3 y las 4 salieron 54 viajes.', bloqueo: null, alternativa: null })
    alternativa.cerrar()

    gestos.emitir('gesto', gesto('rock'))
    await waitFor(() => expect(panel()).toHaveAttribute('aria-hidden', 'true'))
  })

  it('en la demostración pública no hay flujo de la plataforma y el portal no insiste', async () => {
    const espia = simularApi({ 'GET /api/sesion': { autenticado: true } })     // /api/gestos/stream → 404
    renderizarRutas('/no-existe')
    await waitFor(() => expect(espia.mock.calls.some(([url]) => String(url).endsWith('/api/gestos/stream'))).toBe(true))
    await new Promise((r) => setTimeout(r, 100))
    expect(espia.mock.calls.filter(([url]) => String(url).endsWith('/api/gestos/stream'))).toHaveLength(1)
  })

  it('👌 lee la respuesta sin el Markdown', () => {
    expect(textoParaLeer('**54 viajes** entre las 3 y las 4.\n\n| hora | viajes |\n|---|---|\n| 03:00 | 54 |\n\n[fuente](http://x)'))
      .toBe('54 viajes entre las 3 y las 4. hora, viajes. 03:00, 54. fuente')
  })
})
