import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

describe('PaginaDocumentacion', () => {
  it('pinta las secciones, el diagrama y el equipo, con los enlaces del panel cuando responde', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: { grafana: 'http://grafana.local:3000', airflow: 'http://airflow.local:8085' } },
    })
    renderizarRutas('/documentacion')

    expect(await screen.findByRole('heading', { level: 1, name: 'Documentación' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'La plataforma y el escenario E3' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: 'Cómo se protege cada respuesta' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Arquitectura de la plataforma/ })).toBeInTheDocument()
    expect(screen.getByText('1 · Filtro previo del asistente')).toBeInTheDocument()

    const equipo = screen.getByRole('list', { name: 'Equipo' })
    expect(within(equipo).getAllByRole('listitem')).toHaveLength(5)
    expect(within(equipo).getByText('Mónica Fernández')).toBeInTheDocument()

    // Enlaces: los del panel sustituyen a los valores por defecto; el resto conserva el valor del §3.
    await waitFor(() => expect(screen.getByRole('link', { name: 'Grafana' })).toHaveAttribute('href', 'http://grafana.local:3000'))
    expect(screen.getByRole('link', { name: 'Airflow' })).toHaveAttribute('href', 'http://airflow.local:8085')
    expect(screen.getByRole('link', { name: 'API de acceso · /docs' })).toHaveAttribute('href', 'http://localhost:8002/docs')
    expect(screen.getByRole('link', { name: 'Chatbot Chainlit (RAG)' })).toHaveAttribute('href', 'http://localhost:8011')
    expect(screen.getByText(/Enlaces configurados en el BFF/)).toBeInTheDocument()
  })

  it('sin /api/panel usa los enlaces por defecto y lo dice', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/documentacion')

    expect(await screen.findByText(/puertos publicados por defecto/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Grafana' })).toHaveAttribute('href', 'http://localhost:3000')
    expect(screen.getByRole('link', { name: 'Spark (máster)' })).toHaveAttribute('href', 'http://localhost:8090')
    expect(screen.getByRole('link', { name: 'Chatbot Chainlit (Ollama)' })).toHaveAttribute('href', 'http://localhost:8010')
  })
})
