import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

import { CUADROS, urlCuadro, incrustable } from './cuadros'

const PANEL = {
  servicios: [],
  enlaces: { grafana: 'http://localhost:3000' },
}

describe('Observabilidad', () => {
  it('incrusta el cuadro de la plataforma y cambia al de Spark', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': PANEL })
    renderizarRutas('/observabilidad')
    const usuario = userEvent.setup()

    const marco = await screen.findByTitle('Cuadro Plataforma')
    expect(marco).toHaveAttribute('src', urlCuadro('http://localhost:3000', 'pids-plataforma'))
    expect(screen.getByRole('link', { name: 'Abrir Grafana' })).toHaveAttribute('href', 'http://localhost:3000')

    await usuario.click(screen.getByRole('tab', { name: /Spark/ }))
    expect(screen.getByTitle('Cuadro Spark')).toHaveAttribute('src', urlCuadro('http://localhost:3000/', 'pids-spark'))
    expect(CUADROS).toHaveLength(8)
  })

  it('solo incrusta Grafana desde el propio equipo: en la web pública o en la demostración, lo explica', async () => {
    expect(incrustable('http://localhost:3000', 'localhost')).toBe(true)
    expect(incrustable('http://localhost:3000', 'happytaxi-rust.vercel.app')).toBe(false)     // web pública
    expect(incrustable('https://github.com/javiersaguar/PIDS-Proyecto1', 'localhost')).toBe(false)  // demostración
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': { servicios: [], enlaces: { grafana: 'https://github.com/x' } } })
    renderizarRutas('/observabilidad')
    expect(await screen.findByText('Los cuadros se ven desde el equipo de la plataforma')).toBeInTheDocument()
    expect(screen.queryByTitle(/Cuadro/)).not.toBeInTheDocument()
  })

  it('explica que falta la URL en vez de dejar un marco vacío', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': { servicios: [], enlaces: {} } })
    renderizarRutas('/observabilidad')
    expect(await screen.findByText('Grafana no está configurado')).toBeInTheDocument()
    expect(screen.queryByTitle(/Cuadro/)).not.toBeInTheDocument()
  })
})
