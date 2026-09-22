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

  it('con una carga y una simulación en marcha, la barra lo cuenta y el lienzo ilumina sus tramos', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: 900 } },
      'GET /api/operaciones/airflow/ejecuciones': [
        { dag_run_id: 'manual__2', estado: 'running', conf: { mes: '2020-03', muestra: false }, inicio: '2026-09-22T09:58:00+00:00', fin: null },
        { dag_run_id: 'manual__1', estado: 'success', conf: { mes: '2020-02', muestra: false }, inicio: '2026-09-22T09:40:00+00:00', fin: '2026-09-22T09:42:00+00:00' },
      ],
      'GET /api/operaciones/simulacion': {
        activa: true, lote: 'portal-muestra', fichero: 'yellow_tripdata_2020_muestra.csv', enviados: 450, total: 999,
        ritmo: 50, inicio: '2026-09-22T09:59:50+00:00', fin: null, error: null,
      },
    })
    renderizarRutas('/documentacion')

    const barra = await screen.findByRole('status', { name: 'Actividad de la plataforma' })
    await waitFor(() => expect(barra).toHaveTextContent('En marcha ahora'))
    expect(barra).toHaveTextContent(/Carga histórica de marzo de 2020 en ejecución/)
    expect(barra).toHaveTextContent('Simulación en marcha: 450 de 999 viajes · 50 viajes/s')
    expect(barra).not.toHaveTextContent('Spark publicó')          // la frescura de 900 s no cuenta como publicando

    const lienzo = screen.getByRole('region', { name: 'Arquitectura de la plataforma' })
    const activas = [...lienzo.querySelectorAll('[data-activa="true"]')].map((g) => g.getAttribute('data-arista')).sort()
    expect(activas).toEqual(['airflow-s3', 'captura-redpanda', 'redpanda-spark', 's3-spark', 'simulador-captura', 'spark-mongo'])
    expect(lienzo.querySelectorAll('.arista-flujo')).toHaveLength(6)
    expect(lienzo.querySelectorAll('animateMotion').length).toBeGreaterThan(0)
    expect(within(lienzo).getByRole('button', { name: /Airflow/ })).toHaveTextContent('Cargando marzo de 2020')
    expect(within(lienzo).getByRole('button', { name: /Simulador/ })).toHaveTextContent('450 de 999 viajes')
    expect(within(lienzo).getByRole('button', { name: /Grafana/ })).not.toHaveAttribute('data-activo')
  })

  it('sin nada en marcha, la barra dice la última carga y de dónde se lanza algo', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: null } },
      'GET /api/operaciones/airflow/ejecuciones': [
        { dag_run_id: 'manual__1', estado: 'success', conf: { mes: '2020-02', muestra: true }, inicio: '2026-09-22T09:40:00+00:00', fin: '2026-09-22T09:42:00+00:00' },
      ],
      'GET /api/operaciones/simulacion': { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null },
    })
    renderizarRutas('/documentacion')

    const barra = await screen.findByRole('status', { name: 'Actividad de la plataforma' })
    expect(barra).toHaveTextContent('Sin procesos en marcha')
    await waitFor(() => expect(barra).toHaveTextContent(/Última carga: la muestra de prueba \(febrero de 2020\), correcta/))
    expect(within(barra).getByRole('link', { name: 'Lanzar una carga o el simulador' })).toHaveAttribute('href', '/operaciones')
    const lienzo = screen.getByRole('region', { name: 'Arquitectura de la plataforma' })
    expect(lienzo.querySelectorAll('[data-activa="true"]')).toHaveLength(0)
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
