import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { EventoRespuesta, Motor } from '@/api/tipos'
import { cuerpoEnviado, renderizarRutas, simularApi } from '@/pruebas/utilidades'

const MOTORES: Motor[] = [
  { id: 'ollama', nombre: 'Ollama', modelo: 'llama3.1:8b', disponible: true, descripcion: 'Agente local con Ollama' },
  { id: 'rag', nombre: 'RAG', modelo: 'gpt-oss:20b', disponible: false, descripcion: 'Agente con documentación' },
]

const RESPUESTA_BASE: EventoRespuesta = {
  respuesta: '',
  bloqueo: null,
  pasos_llm: 1,
  segundos: 2.61,
  tokens: 12345,
  alternativa: null,
  alternativa_descripcion: null,
  fuentes: [],
}

/** Un `text/event-stream` que el test va alimentando a mano (bloques con `\r\n`, como sse-starlette). */
function flujoSse() {
  let controlador!: ReadableStreamDefaultController<Uint8Array>
  const flujo = new ReadableStream<Uint8Array>({
    start(c) {
      controlador = c
    },
  })
  const codificador = new TextEncoder()
  return {
    respuesta: new Response(flujo, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
    emitir(evento: string, datos: unknown) {
      controlador.enqueue(codificador.encode(`event: ${evento}\r\ndata: ${JSON.stringify(datos)}\r\n\r\n`))
    },
    cerrar() {
      controlador.close()
    },
  }
}

function apiBase(extra: Record<string, unknown> = {}) {
  return simularApi({
    'GET /api/sesion': { autenticado: true },
    'GET /api/chat/motores': MOTORES,
    'POST /api/chat/sesiones': { id: 'ses-1', motor: 'ollama' },
    'DELETE /api/chat/sesiones/ses-1': { status: 204 },
    ...extra,
  } as Parameters<typeof simularApi>[0])
}

describe('PaginaAsistente', () => {
  it('muestra los motores, deshabilita el que no está disponible y abre una sesión con el primero disponible', async () => {
    const espia = apiBase()
    renderizarRutas('/asistente')

    const grupo = await screen.findByRole('radiogroup', { name: 'Motor del asistente' })
    const ollama = within(grupo).getByRole('radio', { name: /Ollama/ })
    const rag = within(grupo).getByRole('radio', { name: /RAG/ })
    expect(ollama).toHaveAttribute('aria-checked', 'true')
    expect(ollama).toHaveTextContent('llama3.1:8b')
    expect(rag).toBeDisabled()
    expect(rag).toHaveTextContent('no disponible')

    await waitFor(() => {
      const creaciones = espia.mock.calls.filter(([url, init]) => String(url).endsWith('/api/chat/sesiones') && init?.method === 'POST')
      expect(creaciones).toHaveLength(1)
      expect(JSON.parse(creaciones[0][1]?.body as string)).toEqual({ motor: 'ollama' })
    })

    // Sugerencias iniciales (las tres preguntas de BIENVENIDA) y el aviso permanente.
    const sugerencias = within(screen.getByRole('list', { name: 'Preguntas de ejemplo' })).getAllByRole('button')
    expect(sugerencias.map((b) => b.textContent)).toEqual([
      '¿Cuántos viajes salieron de JFK el 15 de enero entre las 8 y las 12?',
      '¿Qué barrio tuvo más viajes el 3 de marzo?',
      '¿Cuál fue la propina media en Manhattan la primera semana de febrero?',
    ])
    expect(screen.getAllByText(/no puedo darte información de viajes o personas concretas/).length).toBeGreaterThan(0)
  })

  it('envía con Enter, pinta los pasos en directo y la respuesta en Markdown con segundos y tokens', async () => {
    const flujo = flujoSse()
    const espia = apiBase({ 'POST /api/chat/sesiones/ses-1/mensajes': () => flujo.respuesta })
    renderizarRutas('/asistente')
    const usuario = userEvent.setup()

    const entrada = await screen.findByLabelText('Mensaje para el asistente')
    await waitFor(() => expect(entrada).toBeEnabled())
    await usuario.type(entrada, '¿Qué barrio tuvo más viajes el 3 de marzo?{Enter}')

    // El mensaje del usuario aparece a la derecha y la entrada se bloquea mientras llega la respuesta.
    const hilo = screen.getByRole('log', { name: 'Conversación con el asistente' })
    expect(within(hilo).getByText('¿Qué barrio tuvo más viajes el 3 de marzo?')).toBeInTheDocument()
    expect(entrada).toBeDisabled()
    expect(within(hilo).getByRole('status', { name: 'El asistente está pensando…' })).toBeInTheDocument()
    const envio = espia.mock.calls.find(([url]) => String(url).endsWith('/mensajes'))
    expect(envio).toBeDefined()
    expect(JSON.parse(envio![1]?.body as string)).toEqual({ texto: '¿Qué barrio tuvo más viajes el 3 de marzo?' })
    expect(envio![1]?.credentials).toBe('include')

    // Un paso llega y se ve en directo, con nombre, argumentos y segundos.
    flujo.emitir('paso', {
      nombre: 'consultar_viajes',
      argumentos: { nivel: 'dia_barrio', desde: '2020-03-03T00:00:00', hasta: '2020-03-04T00:00:00' },
      resultado: '{"resumen": {"total_viajes": 203866}}',
      segundos: 0.42,
    })
    expect(await within(hilo).findByRole('button', { name: /Pasos \(1\)/ })).toHaveAttribute('aria-expanded', 'true')
    const lista = within(hilo).getByRole('list', { name: 'Herramientas ejecutadas' })
    expect(within(lista).getByText('consultar_viajes')).toBeInTheDocument()
    expect(within(lista).getByText(/nivel: dia_barrio/)).toBeInTheDocument()
    expect(within(lista).getByText('0,42 s')).toBeInTheDocument()

    // La respuesta final, en Markdown: negrita, tabla y pie de fuente.
    flujo.emitir('respuesta', {
      ...RESPUESTA_BASE,
      respuesta:
        'El barrio con más viajes el 3 de marzo fue **Manhattan**.\n\n| Barrio | Viajes |\n|---|---|\n| Manhattan | 203866 |\n\n_Datos históricos, solo agregados._',
    })
    flujo.cerrar()

    expect(await within(hilo).findByText('Manhattan', { selector: 'strong' })).toBeInTheDocument()
    const tabla = within(hilo).getByRole('table')
    expect(within(tabla).getByRole('columnheader', { name: 'Barrio' })).toBeInTheDocument()
    expect(within(tabla).getByRole('cell', { name: '203866' })).toBeInTheDocument()
    expect(within(hilo).getByText('Datos históricos, solo agregados.')).toBeInTheDocument()
    expect(within(hilo).getByText('2,6 s')).toBeInTheDocument()
    expect(within(hilo).getByText('12.345 tokens')).toBeInTheDocument()
    // Al terminar, los pasos se pliegan pero siguen accesibles.
    expect(within(hilo).getByRole('button', { name: /Pasos \(1\)/ })).toHaveAttribute('aria-expanded', 'false')
    await waitFor(() => expect(entrada).toBeEnabled())
  })

  it('tras un rechazo ofrece la alternativa y «Consultar la alternativa» llama a /alternativa', async () => {
    const primero = flujoSse()
    const segundo = flujoSse()
    const espia = apiBase({
      'POST /api/chat/sesiones/ses-1/mensajes': () => primero.respuesta,
      'POST /api/chat/sesiones/ses-1/alternativa': () => segundo.respuesta,
    })
    renderizarRutas('/asistente')
    const usuario = userEvent.setup()

    const entrada = await screen.findByLabelText('Mensaje para el asistente')
    await waitFor(() => expect(entrada).toBeEnabled())
    await usuario.type(entrada, 'Dame el viaje de las 3:12 desde Times Square el 15 de enero{Enter}')

    primero.emitir('respuesta', {
      ...RESPUESTA_BASE,
      respuesta:
        '🔒 **Consulta rechazada por privacidad**\n- petición de datos individuales\n- la plataforma solo publica agregados de al menos 10 viajes',
      bloqueo: 'filtro_previo',
      pasos_llm: 0,
      segundos: 0.004,
      tokens: null,
      alternativa: { nivel: 'hora_zona', desde: '2020-01-15T03:00:00', hasta: '2020-01-15T04:00:00', zona_origen: 230 },
      alternativa_descripcion: 'viajes por hora desde Times Sq/Theatre District (zona 230) el 15/01/2020 de 03:00 a 04:00 (histórico)',
    })
    primero.cerrar()

    const hilo = screen.getByRole('log', { name: 'Conversación con el asistente' })
    expect(await within(hilo).findByText('Consulta rechazada por privacidad', { selector: 'strong' })).toBeInTheDocument()
    expect(within(hilo).getByText('Filtro de privacidad')).toBeInTheDocument()
    expect(within(hilo).getByText('Filtro previo: rechazada sin pasar por el modelo')).toBeInTheDocument()
    expect(within(hilo).getByText('< 0,01 s')).toBeInTheDocument()
    expect(within(hilo).queryByText(/tokens/)).not.toBeInTheDocument()
    expect(within(hilo).getByText(/viajes por hora desde Times Sq\/Theatre District/)).toBeInTheDocument()
    expect(within(hilo).getByRole('button', { name: '✖ Cancelar' })).toBeInTheDocument()

    await usuario.click(within(hilo).getByRole('button', { name: '✅ Consultar la alternativa' }))

    await waitFor(() => {
      const llamada = espia.mock.calls.find(([url]) => String(url).endsWith('/api/chat/sesiones/ses-1/alternativa'))
      expect(llamada).toBeDefined()
      expect(llamada![1]?.method).toBe('POST')
    })
    expect(within(hilo).getByText(/✅ Consultar la alternativa: viajes por hora/)).toBeInTheDocument()
    expect(within(hilo).queryByRole('button', { name: '✅ Consultar la alternativa' })).not.toBeInTheDocument()
    expect(within(hilo).getByText('Consultada.')).toBeInTheDocument()

    segundo.emitir('respuesta', { ...RESPUESTA_BASE, respuesta: 'Entre las 03:00 y las 04:00 salieron 42 viajes de Times Sq/Theatre District.' })
    segundo.cerrar()
    expect(await within(hilo).findByText(/salieron 42 viajes/)).toBeInTheDocument()
    expect(cuerpoEnviado(espia, espia.mock.calls.findIndex(([url]) => String(url).endsWith('/alternativa')))).toEqual({})
  })

  it('«✖ Cancelar» descarta la alternativa sin llamar al servidor', async () => {
    const flujo = flujoSse()
    const espia = apiBase({ 'POST /api/chat/sesiones/ses-1/mensajes': () => flujo.respuesta })
    renderizarRutas('/asistente')
    const usuario = userEvent.setup()

    const entrada = await screen.findByLabelText('Mensaje para el asistente')
    await waitFor(() => expect(entrada).toBeEnabled())
    await usuario.type(entrada, 'Viajes de JFK a Times Square el 1 de enero{Enter}')
    flujo.emitir('respuesta', {
      ...RESPUESTA_BASE,
      respuesta: '🔒 **Consulta rechazada por privacidad**\n- destino por zona',
      alternativa: { nivel: 'od_dia_barrio', desde: '2020-01-01T00:00:00', hasta: '2020-01-02T00:00:00', barrio_origen: 'Queens', barrio_destino: 'Manhattan' },
      alternativa_descripcion: 'flujos entre barrios desde Queens hacia Manhattan el 01/01/2020 (histórico)',
    })
    flujo.cerrar()

    await usuario.click(await screen.findByRole('button', { name: '✖ Cancelar' }))

    expect(await screen.findByText('De acuerdo, consulta cancelada.')).toBeInTheDocument()
    expect(screen.getByText('Descartada.')).toBeInTheDocument()
    expect(espia.mock.calls.some(([url]) => String(url).endsWith('/alternativa'))).toBe(false)
  })

  it('un evento error del flujo se muestra como alerta en la burbuja', async () => {
    const flujo = flujoSse()
    apiBase({ 'POST /api/chat/sesiones/ses-1/mensajes': () => flujo.respuesta })
    renderizarRutas('/asistente')
    const usuario = userEvent.setup()

    const entrada = await screen.findByLabelText('Mensaje para el asistente')
    await waitFor(() => expect(entrada).toBeEnabled())
    await usuario.type(entrada, 'hola{Enter}')
    flujo.emitir('error', { detail: 'Ollama no responde' })
    flujo.cerrar()

    expect(await screen.findByRole('alert')).toHaveTextContent('Ollama no responde')
    await waitFor(() => expect(entrada).toBeEnabled())
  })

  it('«Nueva conversación» cierra la sesión y abre otra; al salir de la página también se cierra', async () => {
    const espia = apiBase()
    renderizarRutas('/asistente')
    const usuario = userEvent.setup()

    const entrada = await screen.findByLabelText('Mensaje para el asistente')
    await waitFor(() => expect(entrada).toBeEnabled())

    await usuario.click(screen.getByRole('button', { name: 'Nueva conversación' }))
    await waitFor(() => {
      const cierres = espia.mock.calls.filter(([url, init]) => String(url).endsWith('/api/chat/sesiones/ses-1') && init?.method === 'DELETE')
      expect(cierres).toHaveLength(1)
    })
    await waitFor(() => {
      const creaciones = espia.mock.calls.filter(([url, init]) => String(url).endsWith('/api/chat/sesiones') && init?.method === 'POST')
      expect(creaciones).toHaveLength(2)
    })

    await usuario.click(screen.getByRole('link', { name: 'Privacidad' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Privacidad' })).toBeInTheDocument()
    await waitFor(() => {
      const cierres = espia.mock.calls.filter(([url, init]) => String(url).endsWith('/api/chat/sesiones/ses-1') && init?.method === 'DELETE')
      expect(cierres).toHaveLength(2)
    })
  })

  it('sin motores disponibles muestra «no disponible» y con error del BFF, «Reintentar»', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/chat/motores': MOTORES.map((m) => ({ ...m, disponible: false })),
    })
    renderizarRutas('/asistente')
    expect(await screen.findByText('Asistente no disponible')).toBeInTheDocument()
    expect(screen.queryByLabelText('Mensaje para el asistente')).not.toBeInTheDocument()
  })

  it('si /api/chat/motores falla enseña el detail con «Reintentar»', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/chat/motores': { status: 503, json: { detail: 'El motor de chat no está configurado' } },
    })
    renderizarRutas('/asistente')
    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('El motor de chat no está configurado')
    expect(within(alerta).getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })
})
