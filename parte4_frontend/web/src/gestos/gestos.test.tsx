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
  { id: 'rag', nombre: 'RAG', modelo: 'deepseek-v4-flash', disponible: true, descripcion: 'DeepSeek en Helmcode' },
]
const RESPUESTA: EventoRespuesta = {
  respuesta: '', bloqueo: null, pasos_llm: 1, segundos: 1.2, tokens: 100, alternativa: null,
  alternativa_descripcion: null, fuentes: [],
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

const PREGUNTA_AL_AZAR = '¿Cuál fue la propina media en Queens el 4 de julio?'
const gesto = (nombre: string, dispositivo = 'PORTATIL-WINDOWS') =>
  ({ gesto: nombre, confianza: 0.97, dispositivo, instante: '2026-09-22T18:00:00+00:00' })
const panel = () => document.getElementById(ID_PANEL_ASISTENTE)!

describe('gestos de la parte 1 en TAXI AI', () => {
  it('✌️ abre el asistente y pregunta, 👍 cambia de motor, ✋ recorre las secciones sin cerrarlo y ✊ lo cierra', async () => {
    const gestos = flujoSse()
    const turno = flujoSse()
    const espia = simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/gestos/stream': () => gestos.respuesta,
      'GET /api/chat/motores': MOTORES,
      'POST /api/chat/sesiones': (init: RequestInit) => {
        const { motor } = JSON.parse(String(init.body)) as { motor: string }
        return { id: motor === 'rag' ? 'ses-2' : 'ses-1', motor }
      },
      'DELETE /api/chat/sesiones/ses-1': { status: 204 },
      'DELETE /api/chat/sesiones/ses-2': { status: 204 },
      'POST /api/chat/sesiones/ses-1/mensajes': () => turno.respuesta,
      'GET /api/gestos/pregunta': { pregunta: PREGUNTA_AL_AZAR },
    })
    const { enrutador } = renderizarRutas('/no-existe')
    await waitFor(() => expect(espia.mock.calls.some(([url]) => String(url).endsWith('/api/gestos/stream'))).toBe(true))
    expect(panel()).toHaveAttribute('aria-hidden', 'true')
    // el interruptor está en el menú de la izquierda, no en el panel del asistente
    const menu = screen.getByRole('navigation', { name: 'Secciones del portal' }).closest('aside')!
    expect(within(menu).getByRole('button', { name: /Gestos/ })).toHaveAttribute('aria-pressed', 'false')

    // ✌️: abre TAXI AI y hace la pregunta al azar que da el BFF
    gestos.emitir('gesto', gesto('scissors'))
    await waitFor(() => expect(panel()).toHaveAttribute('aria-hidden', 'false'))
    await waitFor(() => {
      const indice = espia.mock.calls.findIndex(([url]) => String(url).endsWith('/mensajes'))
      expect(indice).toBeGreaterThanOrEqual(0)
      expect(cuerpoEnviado(espia, indice)).toEqual({ texto: PREGUNTA_AL_AZAR })   // la del BFF, no las casillas
    })
    turno.emitir('respuesta', { ...RESPUESTA, respuesta: 'La propina media fue de 1,80 dólares.' })
    turno.cerrar()
    await screen.findByText('La propina media fue de 1,80 dólares.')

    // 👍: el de esta pestaña (ya atendido) y uno dudoso no cuentan; el bueno pasa a DeepSeek
    const sesionesRag = () => espia.mock.calls.filter(([url, init]) => String(url).endsWith('/api/chat/sesiones')
      && String((init as RequestInit | undefined)?.body).includes('rag'))
    gestos.emitir('gesto', gesto('thumbsup', DISPOSITIVO))
    gestos.emitir('gesto', { ...gesto('thumbsup'), confianza: 0.4 })
    await new Promise((r) => setTimeout(r, 50))
    expect(sesionesRag()).toHaveLength(0)
    gestos.emitir('gesto', gesto('thumbsup'))
    await waitFor(() => expect(sesionesRag()).toHaveLength(1))
    const motores = await screen.findByRole('radiogroup', { name: 'Motor del asistente' })
    await waitFor(() => expect(within(motores).getByRole('radio', { name: /RAG/ })).toHaveAttribute('aria-checked', 'true'))

    // ✋: de una ruta que no es sección, al Panel; luego al Explorador. TAXI AI no es una sección y sigue abierto
    gestos.emitir('gesto', gesto('paper'))
    await waitFor(() => expect(enrutador.state.location.pathname).toBe('/'))
    gestos.emitir('gesto', { ...gesto('paper'), instante: '2026-09-22T18:00:05+00:00' })
    await waitFor(() => expect(enrutador.state.location.pathname).toBe('/explorador'))
    expect(panel()).toHaveAttribute('aria-hidden', 'false')

    gestos.emitir('gesto', gesto('rock'))
    await waitFor(() => expect(panel()).toHaveAttribute('aria-hidden', 'true'))
  })

  it('si el BFF no da la pregunta de ✌️, hace una de las de siempre', async () => {
    const gestos = flujoSse()
    const espia = simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/gestos/stream': () => gestos.respuesta,
      'GET /api/chat/motores': MOTORES,
      'POST /api/chat/sesiones': { id: 'ses-1', motor: 'ollama' },
      'DELETE /api/chat/sesiones/ses-1': { status: 204 },
      'POST /api/chat/sesiones/ses-1/mensajes': () => flujoSse().respuesta,
      'GET /api/gestos/pregunta': { status: 503, json: { detail: 'caído' } },
    })
    renderizarRutas('/no-existe')
    await waitFor(() => expect(espia.mock.calls.some(([url]) => String(url).endsWith('/api/gestos/stream'))).toBe(true))
    gestos.emitir('gesto', gesto('scissors'))
    await waitFor(() => {
      const indice = espia.mock.calls.findIndex(([url]) => String(url).endsWith('/mensajes'))
      expect(indice).toBeGreaterThanOrEqual(0)
      expect(PREGUNTAS_GESTO).toContain((cuerpoEnviado(espia, indice) as { texto: string }).texto)
    })
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
