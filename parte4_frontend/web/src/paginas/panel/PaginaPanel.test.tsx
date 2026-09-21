import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Panel } from '@/api/tipos'
import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

const PANEL: Panel = {
  ultimo_dia: {
    historico: {
      dia: '2020-12-31T00:00:00',
      por_barrio: { Manhattan: 203866, Queens: 12145, Brooklyn: 1816, Unknown: 1352, Bronx: 233, 'N/A': 80, EWR: 17 },
      total: 219509,
      grupos_enmascarados: 1,
    },
    tiempo_real: { dia: '2020-12-30T00:00:00', por_barrio: { 'N/A': 15, Unknown: 15 }, total: 30, grupos_enmascarados: 0 },
  },
  frescura_tiempo_real: { instante: '2026-09-21T10:15:00+00:00', segundos: 45 },
  consultas_24h: { permitida: 120, enmascarada: 31, rechazada: 9 },
  servicios: [
    { nombre: 'API de acceso', job: 'acceso', estado: 'ok', enlace: 'http://localhost:8002/docs' },
    { nombre: 'Spark', job: 'spark', estado: 'caido' },
    { nombre: 'Airflow', job: 'airflow', estado: 'desconocido' },
  ],
  enlaces: {
    grafana: 'http://localhost:3000',
    airflow: 'http://localhost:8085',
    spark: 'http://localhost:8090',
    chatbot: 'http://localhost:8010',
    chatbot_rag: 'http://localhost:8011',
    api_acceso: 'http://localhost:8002/docs',
    api_captura: 'http://localhost:8001/docs',
  },
  prometheus_disponible: true,
  acceso_disponible: true,
}

function conSesion(panel: unknown) {
  return simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/panel': panel })
}

describe('PaginaPanel', () => {
  it('muestra los KPIs del último día, las decisiones por resultado y la frescura', async () => {
    conSesion(PANEL)
    renderizarRutas('/')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getByText('219.509')).toBeInTheDocument()
    expect(within(indicadores).getByText(/31\/12\/2020 · histórico/)).toBeInTheDocument()
    expect(within(indicadores).getByText('7')).toBeInTheDocument() // barrios
    expect(within(indicadores).getByText(/Manhattan concentra el 92,9 %/)).toBeInTheDocument()

    const decisiones = within(indicadores).getByRole('list', { name: 'Decisiones por resultado' })
    expect(decisiones).toHaveTextContent('120permitida')
    expect(decisiones).toHaveTextContent('31enmascarada')
    expect(decisiones).toHaveTextContent('9rechazada')
    expect(within(indicadores).getByText('160')).toBeInTheDocument()

    // Frescura: 45 s → verde, «al día», y el contador «hace 45 s» (puede haber avanzado un segundo).
    expect(within(indicadores).getByText(/^hace 4[5-7] s$/)).toBeInTheDocument()
    expect(within(indicadores).getByRole('img', { name: 'Estado: al día' })).toBeInTheDocument()
  })

  it('pinta las barras por barrio con pestañas histórico / tiempo real', async () => {
    conSesion(PANEL)
    renderizarRutas('/')
    const usuario = userEvent.setup()

    const grafico = await screen.findByRole('img', { name: 'Viajes por barrio el 31/12/2020 (histórico)' })
    expect(screen.getByText(/7 barrios con grupos visibles/)).toBeInTheDocument()
    // Una barra por barrio, con su cifra al final.
    expect(grafico.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(7)
    expect(grafico).toHaveTextContent('203.866')

    await usuario.click(screen.getByRole('tab', { name: 'Tiempo real' }))
    expect(await screen.findByRole('img', { name: 'Viajes por barrio el 30/12/2020 (tiempo real)' })).toBeInTheDocument()
    expect(screen.getByText(/2 barrios con grupos visibles/)).toBeInTheDocument()
  })

  it('lista los servicios con su estado y los accesos directos en pestaña nueva', async () => {
    conSesion(PANEL)
    renderizarRutas('/')

    const servicios = await screen.findByRole('list', { name: 'Servicios de la plataforma' })
    const filas = within(servicios).getAllByRole('listitem')
    expect(filas).toHaveLength(3)
    expect(filas[0]).toHaveTextContent('API de acceso')
    expect(filas[0]).toHaveTextContent('en marcha')
    expect(filas[1]).toHaveTextContent('caído')
    expect(filas[2]).toHaveTextContent('desconocido')

    const enlaces = screen.getByRole('list', { name: 'Accesos directos' })
    const grafana = within(enlaces).getByRole('link', { name: /Grafana/ })
    expect(grafana).toHaveAttribute('href', 'http://localhost:3000')
    expect(grafana).toHaveAttribute('target', '_blank')
    expect(grafana).toHaveAttribute('rel', 'noreferrer')
    expect(within(enlaces).getAllByRole('link')).toHaveLength(7)
    expect(within(enlaces).getByRole('link', { name: /Chatbot RAG/ })).toHaveAttribute('href', 'http://localhost:8011')
  })

  it('sin Prometheus, las tarjetas que dependen de él dicen «no disponible» y el resto sigue', async () => {
    conSesion({ ...PANEL, prometheus_disponible: false, consultas_24h: null, frescura_tiempo_real: { instante: null, segundos: null } })
    renderizarRutas('/')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getAllByText('Prometheus no disponible')).toHaveLength(2)
    expect(within(indicadores).getByText('219.509')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Viajes por barrio el 31/12/2020 (histórico)' })).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Decisiones por resultado' })).not.toBeInTheDocument()
  })

  it('sin datos publicados ni tiempo real, no rompe: «Sin datos» y estado vacío', async () => {
    conSesion({ ...PANEL, ultimo_dia: { historico: null, tiempo_real: null }, frescura_tiempo_real: { instante: null, segundos: null } })
    renderizarRutas('/')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getAllByText('Sin datos')).toHaveLength(2)
    expect(within(indicadores).getByText('Sin dato')).toBeInTheDocument()
    expect(within(indicadores).getByRole('img', { name: 'Estado: sin datos recientes' })).toBeInTheDocument()
    expect(screen.getByText('Sin datos de histórico')).toBeInTheDocument()
  })

  it('si la API de acceso no responde (acceso_disponible: false), lo dice en vez de «Sin datos»', async () => {
    conSesion({ ...PANEL, ultimo_dia: { historico: null, tiempo_real: null }, acceso_disponible: false })
    renderizarRutas('/')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getAllByText('API de acceso no disponible')).toHaveLength(2)
    expect(within(indicadores).queryByText('Sin datos')).not.toBeInTheDocument()
    expect(screen.getAllByText('API de acceso no disponible')).toHaveLength(3) // las dos tarjetas y el gráfico
    // Prometheus sí responde: las decisiones siguen ahí.
    expect(within(indicadores).getByText('160')).toBeInTheDocument()
  })

  it('si el BFF falla, muestra el error con «Reintentar» y al pulsarlo vuelve a pedir el panel', async () => {
    let intentos = 0
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': () => {
        intentos += 1
        return intentos === 1 ? { status: 502, json: { detail: 'La API de acceso no responde' } } : PANEL
      },
    })
    renderizarRutas('/')
    const usuario = userEvent.setup()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('No se ha podido cargar el panel')
    expect(alerta).toHaveTextContent('La API de acceso no responde')

    await usuario.click(within(alerta).getByRole('button', { name: 'Reintentar' }))
    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getByText('219.509')).toBeInTheDocument()
    expect(intentos).toBe(2)
  })
})
