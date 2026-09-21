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

describe('AppShell', () => {
  it('pinta la navegación con las siete secciones y marca la activa', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL })
    renderizarRutas('/explorador')

    const navegacion = await screen.findByRole('navigation', { name: 'Secciones del portal' })
    const enlaces = within(navegacion).getAllByRole('link')
    expect(enlaces.map((e) => e.textContent)).toEqual(SECCIONES.map((s) => s.titulo))
    expect(enlaces).toHaveLength(7)
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
