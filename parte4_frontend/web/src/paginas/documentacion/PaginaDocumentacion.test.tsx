import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

describe('PaginaDocumentacion', () => {
  it('pinta el lienzo y, al pulsar una pieza, explica qué es y abre el enlace del panel', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: { grafana: 'http://grafana.local:3000', airflow: 'http://airflow.local:8085' } },
    })
    renderizarRutas('/documentacion')
    const usuario = userEvent.setup()

    const lienzo = await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    expect(within(lienzo).getByRole('button', { name: /Redpanda/ })).toBeInTheDocument()
    expect(within(lienzo).getByRole('button', { name: /API de acceso/ })).toBeInTheDocument()
    expect(within(lienzo).getByRole('button', { name: /Spark/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'La plataforma y el escenario E3' })).not.toBeInTheDocument()

    await usuario.click(within(lienzo).getByRole('button', { name: /Redpanda/ }))
    const ficha = await screen.findByRole('dialog')
    expect(within(ficha).getByRole('heading', { name: 'Redpanda' })).toBeInTheDocument()
    expect(within(ficha).getByText('Qué es')).toBeInTheDocument()
    expect(within(ficha).getByText('Qué hace')).toBeInTheDocument()
    expect(within(ficha).getByText('Cómo se conecta aquí')).toBeInTheDocument()
    expect(within(ficha).getByText(/sala de espera|cola de lo que acaba de llegar/i)).toBeInTheDocument()

    await usuario.click(within(ficha).getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Grafana/ }))
    await waitFor(() => expect(screen.getByRole('link', { name: 'Abrir Grafana' })).toHaveAttribute('href', 'http://grafana.local:3000'))

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Airflow/ }))
    expect(await screen.findByRole('link', { name: 'Abrir Airflow' })).toHaveAttribute('href', 'http://airflow.local:8085')
  })

  it('sin /api/panel usa los enlaces por defecto', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/documentacion')
    const usuario = userEvent.setup()

    const lienzo = await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    await usuario.click(within(lienzo).getByRole('button', { name: /Spark/ }))
    const fichaSpark = await screen.findByRole('dialog')
    expect(within(fichaSpark).getByRole('heading', { name: 'Spark' })).toBeInTheDocument()
    expect(within(fichaSpark).queryByRole('link', { name: 'Abrir Spark' })).not.toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /API de acceso/ }))
    expect(await screen.findByRole('link', { name: 'Abrir la API de acceso' })).toHaveAttribute('href', 'http://localhost:8002/docs')

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Chatbots/ }))
    expect(await screen.findByRole('link', { name: 'Abrir con Ollama' })).toHaveAttribute('href', 'http://localhost:8010')
    expect(screen.getByRole('link', { name: 'Abrir con documentación' })).toHaveAttribute('href', 'http://localhost:8011')
  })
})
