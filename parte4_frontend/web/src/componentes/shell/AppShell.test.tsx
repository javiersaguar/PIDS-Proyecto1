import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

import { SECCIONES } from './navegacion'

const PANEL = {
  servicios: [
    { nombre: 'API de acceso', job: 'acceso', estado: 'ok' },
    { nombre: 'Prometheus', job: 'prometheus', estado: 'caido' },
  ],
}
const CHAT = {
  'GET /api/chat/motores': [{ id: 'ollama', nombre: 'Ollama', modelo: 'llama3.1:8b', disponible: true, descripcion: 'Agente local' }],
  'POST /api/chat/sesiones': { id: 'ses-1', motor: 'ollama' },
  'DELETE /api/chat/sesiones/ses-1': { status: 204 },
}

describe('AppShell', () => {
  it('pinta la navegación con las secciones (sin el asistente) y marca la activa', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL })
    renderizarRutas('/explorador')

    const navegacion = await screen.findByRole('navigation', { name: 'Secciones del portal' })
    const enlaces = within(navegacion).getAllByRole('link')
    expect(enlaces.map((e) => e.textContent)).toEqual(SECCIONES.map((s) => s.titulo))
    expect(enlaces).toHaveLength(SECCIONES.length)
    expect(within(navegacion).queryByRole('link', { name: 'Asistente' })).not.toBeInTheDocument()
    expect(within(navegacion).getByRole('link', { name: 'Explorador' })).toHaveAttribute('aria-current', 'page')
    expect(within(navegacion).getByRole('link', { name: 'Panel' })).not.toHaveAttribute('aria-current')

    expect(screen.getByText('PIDS · Taxis NYC')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Explorador' })).toBeInTheDocument()
    expect(screen.queryByText('Solo agregados protegidos · k = 10')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
  })

  it('muestra los chips de estado de los servicios cuando /api/panel responde', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL })
    renderizarRutas('/no-existe')

    const lista = await screen.findByRole('list', { name: 'Estado de los servicios' })
    expect(within(lista).getByText('API de acceso')).toBeInTheDocument()
    expect(within(lista).getByText('Prometheus')).toBeInTheDocument()
  })

  it('en operaciones no pinta la cabecera de servicios', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': PANEL,
      'GET /api/operaciones/airflow/ejecuciones': [],
      'GET /api/operaciones/simulacion': { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null },
      'GET /api/operaciones/simulacion/ficheros': [],
    })
    renderizarRutas('/operaciones')

    expect(await screen.findByRole('heading', { level: 1, name: 'Operaciones' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Carga histórica' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Simulador de tiempo real' })).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Estado de los servicios' })).not.toBeInTheDocument()
  })

  it('en tiempo real no pinta la cabecera de servicios', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL, 'GET /api/tiempo-real': { frescura: { instante: null, segundos: null }, ultimo_dia: null, por_hora: [], por_zona_ultima_hora: [] } })
    renderizarRutas('/tiempo-real')

    expect(await screen.findByRole('heading', { level: 1, name: 'Tiempo real' })).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Estado de los servicios' })).not.toBeInTheDocument()
    expect(screen.queryByText('Solo agregados protegidos · k = 10')).not.toBeInTheDocument()
  })

  it('no muestra chips ni rompe si /api/panel todavía no existe', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/privacidad')

    expect(await screen.findByRole('heading', { level: 1, name: 'Privacidad' })).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('list', { name: 'Estado de los servicios' })).not.toBeInTheDocument())
  })

  it('una ruta desconocida enseña «No encontrado» dentro del shell', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/no-existe')

    expect(await screen.findByRole('heading', { level: 1, name: 'Página no encontrada' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Secciones del portal' })).toBeInTheDocument()
  })

  it('el botón TAXI AI abre el panel del asistente sin cambiar de ruta y lo cierra con el mismo botón o con Escape', async () => {
    const espia = simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL, ...CHAT })
    renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    const boton = await screen.findByRole('button', { name: 'Abrir TAXI AI, el asistente de datos' })
    expect(boton).toHaveTextContent('TAXI AI')
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    const panel = screen.getByLabelText('TAXI AI, asistente de datos')
    expect(panel).toHaveAttribute('aria-hidden', 'true')
    // Cerrado y sin abrir nunca, el chat no existe: ni motores ni sesión en el BFF.
    expect(espia.mock.calls.some(([url]) => String(url).includes('/api/chat/'))).toBe(false)

    await usuario.click(boton)

    expect(panel).toHaveAttribute('aria-hidden', 'false')
    expect(boton).toHaveAttribute('aria-expanded', 'true')
    // Con el panel abierto el botón flotante se esconde: no queda otro botón encima de la página
    expect(boton).toHaveClass('invisible')
    expect(boton).toHaveAttribute('aria-hidden', 'true')
    expect(screen.queryByRole('button', { name: /TAXI AI/ })).not.toBeInTheDocument()
    expect(within(panel).getByRole('heading', { level: 2, name: 'TAXI AI' })).toBeInTheDocument()
    expect(await within(panel).findByRole('radiogroup', { name: 'Motor del asistente' })).toBeInTheDocument()
    // Sigue en el explorador: el panel no navega.
    expect(screen.getByRole('heading', { level: 1, name: 'Explorador' })).toBeInTheDocument()

    await usuario.keyboard('{Escape}')
    expect(panel).toHaveAttribute('aria-hidden', 'true')
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    expect(boton).not.toHaveClass('invisible')
  })

  it('la X del panel lo cierra y devuelve el foco al botón; el panel sigue montado con su conversación', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL, ...CHAT })
    renderizarRutas('/')
    const usuario = userEvent.setup()

    const boton = await screen.findByRole('button', { name: 'Abrir TAXI AI, el asistente de datos' })
    await usuario.click(boton)
    const panel = screen.getByRole('complementary', { name: 'TAXI AI, asistente de datos' })
    const cerrar = await within(panel).findByRole('button', { name: 'Cerrar el asistente' })
    await usuario.click(cerrar)

    expect(panel).toHaveAttribute('aria-hidden', 'true')
    expect(boton).toHaveFocus()
    // El chat no se desmonta al cerrar: la cabecera del asistente sigue en el DOM (oculta).
    expect(within(panel).getByRole('heading', { level: 2, name: 'TAXI AI', hidden: true })).toBeInTheDocument()
  })

  it('el panel abierto se mantiene al cambiar de sección', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL, ...CHAT })
    renderizarRutas('/')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Abrir TAXI AI, el asistente de datos' }))
    await usuario.click(screen.getByRole('link', { name: 'Privacidad' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Privacidad' })).toBeInTheDocument()
    expect(screen.getByRole('complementary', { name: 'TAXI AI, asistente de datos' })).toHaveAttribute('aria-hidden', 'false')
  })

  it('la ruta antigua /asistente vuelve a la portada con el panel abierto', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL, ...CHAT })
    renderizarRutas('/asistente')

    expect(await screen.findByRole('heading', { level: 1, name: 'Panel' })).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('complementary', { name: 'TAXI AI, asistente de datos' })).toHaveAttribute('aria-hidden', 'false'),
    )
  })

  it('cerrar sesión llama a DELETE /api/sesion y vuelve al acceso', async () => {
    let autenticado = true
    const espia = simularApi({
      'GET /api/sesion': () => ({ autenticado }),
      'DELETE /api/sesion': () => {
        autenticado = false
        return { status: 204 }
      },
    })
    renderizarRutas('/')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))

    expect(await screen.findByText('Acceso al portal')).toBeInTheDocument()
    const metodos = espia.mock.calls.map(([, init]) => (init as RequestInit | undefined)?.method ?? 'GET')
    expect(metodos).toContain('DELETE')
  })
})
